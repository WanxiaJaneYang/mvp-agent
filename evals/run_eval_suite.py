from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.agent.pipeline.stage8_validation import run_stage8_citation_validation
from apps.agent.retrieval.evidence_pack import build_evidence_pack
from apps.agent.synthesis.postprocess import CORE_SECTIONS, finalize_validation_outcome


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


def _run_retrieval_case(case: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    result = build_evidence_pack(
        fts_rows=case["fts_rows"],
        query_text=case["query_text"],
        pack_size=case.get("pack_size", 30),
    )

    expected_chunk_ids = case["expected"].get("chunk_ids")
    if expected_chunk_ids is not None:
        actual_chunk_ids = [row["chunk_id"] for row in result]
        if actual_chunk_ids != expected_chunk_ids:
            errors.append(f"expected chunk_ids={expected_chunk_ids}, got {actual_chunk_ids}")

    expected_pack_size = case["expected"].get("pack_size")
    if expected_pack_size is not None and len(result) != expected_pack_size:
        errors.append(f"expected pack_size={expected_pack_size}, got {len(result)}")

    return errors


def _run_postprocess_case(case: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    result = finalize_validation_outcome(validation_result=case["validation_result"])

    expected_status = case["expected"]["status"]
    if result["status"] != expected_status:
        errors.append(f"expected status={expected_status}, got {result['status']}")

    expected_reason = case["expected"].get("abstain_reason")
    if expected_reason is not None and result["abstain_reason"] != expected_reason:
        errors.append(f"expected abstain_reason={expected_reason}, got {result['abstain_reason']}")

    expected_core_text = case["expected"].get("core_section_text")
    if expected_core_text is not None:
        for section in CORE_SECTIONS:
            section_text = result["synthesis"][section][0]["text"]
            if section_text != expected_core_text:
                errors.append(f"expected {section}[0].text={expected_core_text}, got {section_text}")

    return errors


def _run_case(case: Dict[str, Any]) -> List[str]:
    case_id = case.get("id", "unknown")
    case_type = case.get("type")
    try:
        if case_type == "citation":
            return [f"{case_id}: {error}" for error in _run_citation_case(case)]
        if case_type == "retrieval":
            return [f"{case_id}: {error}" for error in _run_retrieval_case(case)]
        if case_type == "postprocess":
            return [f"{case_id}: {error}" for error in _run_postprocess_case(case)]
        return [f"{case_id}: unknown case type: {case_type}"]
    except Exception as exc:
        return [f"{case_id}: exception: {exc}"]


def main() -> int:
    golden_dir = ROOT / "evals" / "golden"
    cases = _load_cases(golden_dir)

    if len(cases) < 10:
        print(f"FAIL: expected >=10 golden cases, found {len(cases)}")
        return 1

    failures: List[str] = []
    for case in cases:
        failures.extend(_run_case(case))

    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"PASS: {len(cases)} golden cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
