from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUN_KIND_BASE_DIRS = {
    "fixture": Path(".tmp_repo_dashboard/demo"),
    "evals": None,
    "targeted_tests": None,
    "live": Path(".tmp_repo_dashboard/live"),
}


def discover_dashboard_artifacts(*, repo_root: Path) -> dict[str, Any]:
    by_kind: dict[str, dict[str, Any]] = {}
    for run_kind, relative_base in RUN_KIND_BASE_DIRS.items():
        if relative_base is None:
            by_kind[run_kind] = _empty_entry(run_kind)
            continue
        by_kind[run_kind] = _discover_run_kind(repo_root=repo_root, run_kind=run_kind, base_dir=repo_root / relative_base)
    latest = _select_latest(by_kind)
    return {"refreshed_at_utc": _utc_now_iso(), "by_kind": by_kind, "latest": latest}


def _discover_run_kind(*, repo_root: Path, run_kind: str, base_dir: Path) -> dict[str, Any]:
    brief_path = _latest_path(base_dir.glob("artifacts/daily/*/brief.html"))
    decision_record_path = _latest_path(base_dir.glob("artifacts/decision_records/*/*.json"))
    summary_path = _latest_path(base_dir.glob("artifacts/runtime/daily_brief_runs/*/*/run_summary.json"))

    publish_decision = None
    reason_codes: list[str] = []
    reason = None
    if decision_record_path is not None:
        decision_payload = _read_json(decision_record_path)
        publish_decision = _string_or_none(decision_payload.get("publish_decision"))
        reason_codes = [str(code) for code in decision_payload.get("reason_codes", []) if str(code).strip()]
        rationale = decision_payload.get("decision_rationale", {})
        if isinstance(rationale, dict):
            reason = _string_or_none(rationale.get("summary"))
    if summary_path is not None:
        summary_payload = _read_json(summary_path)
        publish_decision = _string_or_none(summary_payload.get("publish_decision")) or publish_decision
        if not reason_codes:
            reason_codes = [str(code) for code in summary_payload.get("reason_codes", []) if str(code).strip()]
        if reason is None:
            guardrail_checks = summary_payload.get("guardrail_checks", {})
            if isinstance(guardrail_checks, dict):
                notes = guardrail_checks.get("notes", [])
                if isinstance(notes, list) and notes:
                    reason = _string_or_none(notes[0])

    updated_path = _latest_path(path for path in (brief_path, decision_record_path, summary_path) if path is not None)
    updated_at_utc = None if updated_path is None else _stat_time(updated_path)
    return {
        "run_kind": run_kind,
        "status": "ok" if updated_path is not None else "idle",
        "base_dir": str(base_dir),
        "brief_html_path": None if brief_path is None else str(brief_path),
        "brief_html_uri": None if brief_path is None else brief_path.resolve().as_uri(),
        "decision_record_path": None if decision_record_path is None else str(decision_record_path),
        "decision_record_uri": None if decision_record_path is None else decision_record_path.resolve().as_uri(),
        "run_summary_path": None if summary_path is None else str(summary_path),
        "run_summary_uri": None if summary_path is None else summary_path.resolve().as_uri(),
        "publish_decision": publish_decision,
        "reason": reason,
        "reason_codes": reason_codes,
        "updated_at_utc": updated_at_utc,
        "artifact_paths": {
            key: value
            for key, value in {
                "brief_html": None if brief_path is None else str(brief_path),
                "decision_record": None if decision_record_path is None else str(decision_record_path),
                "run_summary": None if summary_path is None else str(summary_path),
            }.items()
            if value is not None
        },
    }


def _select_latest(by_kind: dict[str, dict[str, Any]]) -> dict[str, Any]:
    populated = [entry for entry in by_kind.values() if entry.get("updated_at_utc")]
    if not populated:
        return _empty_entry("latest")
    latest = max(populated, key=lambda entry: str(entry["updated_at_utc"]))
    return dict(latest)


def _latest_path(paths: Any) -> Path | None:
    candidates = [Path(path) for path in paths]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _stat_time(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def _empty_entry(run_kind: str) -> dict[str, Any]:
    return {
        "run_kind": run_kind,
        "status": "idle",
        "base_dir": None,
        "brief_html_path": None,
        "brief_html_uri": None,
        "decision_record_path": None,
        "decision_record_uri": None,
        "run_summary_path": None,
        "run_summary_uri": None,
        "publish_decision": None,
        "reason": None,
        "reason_codes": [],
        "updated_at_utc": None,
        "artifact_paths": {},
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
