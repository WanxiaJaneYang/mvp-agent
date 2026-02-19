from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "decision_record.v1"
RUN_TYPES = {"daily_brief", "alert"}
STATUSES = {"ok", "partial", "abstained", "failed"}
CLAIM_SECTIONS = {"prevailing", "counter", "minority", "watch", "changed"}
COVERAGE_STATUSES = {"supported", "insufficient_evidence", "removed"}
GUARDRAIL_LEVELS = {"pass", "warn", "fail"}
CONFIDENCE_LABELS = {"high", "medium", "low"}

EXAMPLE_PATH = Path("artifacts/modelling/examples/decision_record_v1.example.json")


def _is_iso_utc(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _require(record: dict[str, Any], key: str, expected_type: type, errors: list[str]) -> Any:
    value = record.get(key)
    if value is None:
        errors.append(f"Missing required field: {key}")
        return None
    if not isinstance(value, expected_type):
        errors.append(f"Field {key} must be {expected_type.__name__}")
        return None
    return value


def validate_decision_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")

    run_type = record.get("run_type")
    if run_type not in RUN_TYPES:
        errors.append("run_type must be one of: daily_brief, alert")

    status = record.get("status")
    if status not in STATUSES:
        errors.append("status must be one of: ok, partial, abstained, failed")

    if not _is_iso_utc(record.get("generated_at_utc")):
        errors.append("generated_at_utc must be an ISO-8601 UTC timestamp")

    for required in ("record_id", "run_id"):
        _require(record, required, str, errors)

    claims = _require(record, "claims", list, errors) or []
    for claim in claims:
        if not isinstance(claim, dict):
            errors.append("claims entries must be objects")
            continue

        coverage = claim.get("coverage_status")
        if coverage not in COVERAGE_STATUSES:
            errors.append("claim coverage_status must be supported|insufficient_evidence|removed")

        section = claim.get("section")
        if section not in CLAIM_SECTIONS:
            errors.append("claim section must be prevailing|counter|minority|watch|changed")

        citation_ids = claim.get("citation_ids")
        if not isinstance(citation_ids, list) or not all(isinstance(v, str) for v in citation_ids):
            errors.append("claim citation_ids must be an array of strings")
            citation_ids = []

        if coverage == "supported" and len(citation_ids) < 1:
            errors.append("supported claim must include at least one citation_id")

    budget = _require(record, "budget_snapshot", dict, errors) or {}
    if budget:
        spend_cap_pairs = (
            ("hourly_spend_usd", "hourly_cap_usd"),
            ("daily_spend_usd", "daily_cap_usd"),
            ("monthly_spend_usd", "monthly_cap_usd"),
        )
        for spend_key, cap_key in spend_cap_pairs:
            spend = budget.get(spend_key)
            cap = budget.get(cap_key)
            if not isinstance(spend, (int, float)):
                errors.append(f"budget_snapshot.{spend_key} must be numeric")
            if not isinstance(cap, (int, float)):
                errors.append(f"budget_snapshot.{cap_key} must be numeric")

        allowed = budget.get("allowed")
        if not isinstance(allowed, bool):
            errors.append("budget_snapshot.allowed must be boolean")
        else:
            cap_reached = any(
                isinstance(budget.get(spend_key), (int, float))
                and isinstance(budget.get(cap_key), (int, float))
                and budget[spend_key] >= budget[cap_key]
                for spend_key, cap_key in spend_cap_pairs
            )
            if cap_reached and allowed:
                errors.append("budget_snapshot.allowed must be false when spend reaches/exceeds cap")

    guardrail = _require(record, "guardrail_checks", dict, errors) or {}
    if guardrail:
        for key in ("citation_check", "paywall_check", "diversity_check", "budget_check"):
            value = guardrail.get(key)
            if value not in GUARDRAIL_LEVELS:
                errors.append(f"guardrail_checks.{key} must be pass|warn|fail")
        notes = guardrail.get("notes")
        if not isinstance(notes, list) or not all(isinstance(item, str) for item in notes):
            errors.append("guardrail_checks.notes must be an array of strings")

    artifacts = _require(record, "artifacts", dict, errors) or {}
    if status != "failed":
        output_sha = artifacts.get("output_sha256")
        if not isinstance(output_sha, str) or not output_sha:
            errors.append("artifacts.output_sha256 is required when status != failed")

    rationale = _require(record, "decision_rationale", dict, errors) or {}
    if rationale:
        confidence = rationale.get("confidence_label")
        if confidence not in CONFIDENCE_LABELS:
            errors.append("decision_rationale.confidence_label must be high|medium|low")

        uncertainties = rationale.get("uncertainties")
        if not isinstance(uncertainties, list) or not all(isinstance(v, str) for v in uncertainties):
            errors.append("decision_rationale.uncertainties must be an array of strings")
            uncertainties = []
        if status == "abstained" and len(uncertainties) == 0:
            errors.append("abstained status requires non-empty decision_rationale.uncertainties")

    _require(record, "rejected_alternatives", list, errors)
    _require(record, "risk_flags", list, errors)

    return errors


def validate_example_file(path: Path = EXAMPLE_PATH) -> list[str]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            record = json.load(handle)
    except FileNotFoundError:
        return [f"Example file not found: {path}"]
    except json.JSONDecodeError as error:
        return [f"Invalid JSON in {path}: {error}"]

    if not isinstance(record, dict):
        return [f"Top-level JSON object required in {path}"]

    return validate_decision_record(record)


def main() -> None:
    errors = validate_example_file()
    if errors:
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("Decision record schema validation passed.")


if __name__ == "__main__":
    main()
