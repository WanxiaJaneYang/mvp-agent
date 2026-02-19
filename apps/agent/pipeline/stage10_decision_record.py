from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_status(stage8_status: str) -> str:
    if stage8_status == "retry":
        return "abstained"
    if stage8_status in {"ok", "partial", "failed", "abstained"}:
        return stage8_status
    return "failed"


def build_and_persist_decision_record(
    *,
    base_dir: Path,
    run_id: str,
    run_type: str,
    stage8_status: str,
    synthesis: Mapping[str, Any],
    removed_bullets: int,
    budget_snapshot: Mapping[str, Any],
    guardrail_checks: Mapping[str, Any],
    output_path: Path | None = None,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    timestamp = generated_at_utc or _utc_now_iso()
    date_partition = timestamp[:10]
    status = _normalize_status(stage8_status)

    claims: list[dict[str, Any]] = []
    claim_counter = 1
    for section, bullets in synthesis.items():
        if not isinstance(bullets, list):
            continue
        for bullet in bullets:
            if not isinstance(bullet, Mapping):
                continue
            citation_ids = bullet.get("citation_ids")
            if not isinstance(citation_ids, list):
                citation_ids = []
            claim = {
                "claim_id": f"c_{claim_counter:03d}",
                "section": str(section),
                "text": str(bullet.get("text", "")),
                "citation_ids": citation_ids,
                "coverage_status": "supported" if len(citation_ids) >= 1 else "insufficient_evidence",
            }
            claims.append(claim)
            claim_counter += 1

    rejected_alternatives: list[dict[str, str]] = []
    if removed_bullets > 0:
        rejected_alternatives.append(
            {
                "candidate_summary": "Claim candidates removed by citation validation",
                "reason_code": "insufficient_evidence",
                "notes": f"{removed_bullets} claim(s) removed or downgraded at stage 8",
            }
        )

    risk_flags = []
    for key, value in guardrail_checks.items():
        if key.endswith("_check") and value in {"warn", "fail"}:
            risk_flags.append(key.replace("_check", ""))

    artifacts: dict[str, Any] = {}
    if output_path is not None:
        artifacts["output_path"] = str(output_path)
        if output_path.exists():
            artifacts["output_sha256"] = _hash_file(output_path)
            artifacts["synthesis_id"] = f"syn_{run_id}"
    if status != "failed" and "output_sha256" not in artifacts:
        artifacts["output_sha256"] = ""

    uncertainties: list[str] = []
    if status == "abstained":
        uncertainties.append("Synthesis required retry/abstain after citation validation.")
    if removed_bullets > 0:
        uncertainties.append(f"{removed_bullets} claim(s) had insufficient evidence coverage.")

    decision_record = {
        "schema_version": "decision_record.v1",
        "record_id": f"dr_{run_id}",
        "run_id": run_id,
        "run_type": run_type,
        "generated_at_utc": timestamp,
        "status": status,
        "claims": claims,
        "rejected_alternatives": rejected_alternatives,
        "risk_flags": risk_flags,
        "budget_snapshot": dict(budget_snapshot),
        "guardrail_checks": dict(guardrail_checks),
        "artifacts": artifacts,
        "decision_rationale": {
            "summary": "Decision record generated from pipeline stage outputs.",
            "confidence_label": "medium" if removed_bullets > 0 else "high",
            "key_drivers": ["citation_validation", "budget_guard", "guardrail_checks"],
            "uncertainties": uncertainties,
        },
    }

    records_dir = base_dir / "artifacts" / "decision_records" / date_partition
    records_dir.mkdir(parents=True, exist_ok=True)
    record_path = records_dir / f"{run_id}.json"
    record_path.write_text(json.dumps(decision_record, indent=2), encoding="utf-8")

    return {"record_path": str(record_path), "decision_record": decision_record}
