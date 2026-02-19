from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.agent.pipeline.stage8_validation import run_stage8_citation_validation
from apps.agent.runtime.budget_guard import evaluate_budget_guard


def _load_cases(golden_dir: Path) -> List[Dict[str, Any]]:
    case_files = sorted(golden_dir.glob("case*.json"))
    return [json.loads(path.read_text(encoding="utf-8")) for path in case_files]


def _run_citation_case(case: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    result = run_stage8_citation_validation(case["synthesis"], case["citation_store"])

    expected_status = case["expected"]["status"]
    if result["status"] != expected_status:
        errors.append(f"expected status={expected_status}, got {result['status']}")

    expected_removed = case["expected"].get("removed_bullets")
    if expected_removed is not None and result["report"]["removed_bullets"] != expected_removed:
        errors.append(
            f"expected removed_bullets={expected_removed}, got {result['report']['removed_bullets']}"
        )

    return errors


def _run_budget_case(case: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    decision = evaluate_budget_guard(
        hourly_spend_usd=case["inputs"]["hourly_spend_usd"],
        daily_spend_usd=case["inputs"]["daily_spend_usd"],
        monthly_spend_usd=case["inputs"]["monthly_spend_usd"],
        next_estimated_cost_usd=case["inputs"]["next_estimated_cost_usd"],
    )

    expected_allowed = case["expected"]["allowed"]
    if decision.allowed != expected_allowed:
        errors.append(f"expected allowed={expected_allowed}, got {decision.allowed}")

    expected_exceeded = case["expected"].get("exceeded_windows")
    if expected_exceeded is not None and decision.exceeded_windows != expected_exceeded:
        errors.append(
            f"expected exceeded_windows={expected_exceeded}, got {decision.exceeded_windows}"
        )

    return errors


def main() -> int:
    golden_dir = Path("evals") / "golden"
    cases = _load_cases(golden_dir)

    if len(cases) < 10:
        print(f"FAIL: expected >=10 golden cases, found {len(cases)}")
        return 1

    failures: List[str] = []
    for case in cases:
        case_id = case.get("id", "unknown")
        case_type = case.get("type")

        if case_type == "citation":
            errors = _run_citation_case(case)
        elif case_type == "budget":
            errors = _run_budget_case(case)
        else:
            errors = [f"unknown case type: {case_type}"]

        for error in errors:
            failures.append(f"{case_id}: {error}")

    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"PASS: {len(cases)} golden cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
