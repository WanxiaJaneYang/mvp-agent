from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.agent.pipeline.stage8_validation import run_stage8_citation_validation  # noqa: E402
from apps.agent.retrieval.evidence_pack import build_evidence_pack  # noqa: E402
from apps.agent.synthesis.postprocess import CORE_SECTIONS, finalize_validation_outcome  # noqa: E402

SUPPORTED_NOVELTY_LABELS = {
    "new",
    "continued",
    "reframed",
    "weakened",
    "strengthened",
    "reversed",
}
QUESTION_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "change",
    "does",
    "few",
    "for",
    "how",
    "in",
    "is",
    "keep",
    "latest",
    "near",
    "next",
    "of",
    "on",
    "or",
    "term",
    "the",
    "this",
    "to",
    "what",
    "weeks",
    "will",
}
TEMPLATED_WHY_IT_MATTERS = {
    "investors should watch this closely.",
    "investors should watch this closely",
    "this could move markets.",
    "this could move markets",
}


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
        synthesis_view = _core_section_view(result["synthesis"])
        for section in CORE_SECTIONS:
            section_bullets = synthesis_view.get(section, [])
            section_text = section_bullets[0]["text"]
            if section_text != expected_core_text:
                errors.append(f"expected {section}[0].text={expected_core_text}, got {section_text}")

    return errors


def _run_literature_review_case(case: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    synthesis = case["synthesis"]
    expected = case["expected"]
    actual_reason_codes = _literature_review_reason_codes(synthesis)
    expected_passes = bool(expected.get("passes", True))
    actual_passes = len(actual_reason_codes) == 0
    if actual_passes != expected_passes:
        errors.append(f"expected passes={expected_passes}, got {actual_passes}")

    expected_reason_codes = expected.get("reason_codes")
    if isinstance(expected_reason_codes, list):
        if actual_reason_codes != expected_reason_codes:
            errors.append(f"expected reason_codes={expected_reason_codes}, got {actual_reason_codes}")
    return errors


def _core_section_view(synthesis: Dict[str, Any]) -> Dict[str, Any]:
    issues = synthesis.get("issues")
    if isinstance(issues, list) and issues:
        first_issue = issues[0]
        if isinstance(first_issue, dict):
            return first_issue
    return synthesis


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
        if case_type == "literature_review":
            return [f"{case_id}: {error}" for error in _run_literature_review_case(case)]
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


def _literature_review_reason_codes(synthesis: Dict[str, Any]) -> List[str]:
    reason_codes: List[str] = []
    brief = synthesis.get("brief")
    if not isinstance(brief, dict):
        reason_codes.append("missing_top_summary")
    else:
        bottom_line = str(brief.get("bottom_line") or "").strip()
        takeaways = brief.get("top_takeaways")
        takeaway_items = (
            [item for item in takeaways if str(item).strip()]
            if isinstance(takeaways, list)
            else []
        )
        if not bottom_line or not takeaway_items:
            reason_codes.append("missing_top_summary")

    issues = synthesis.get("issues", [])
    normalized_questions = set()
    for issue in issues if isinstance(issues, list) else []:
        if not isinstance(issue, dict):
            continue
        issue_question = str(issue.get("issue_question") or issue.get("title") or "").strip().lower()
        issue_tokens = _normalized_tokens(issue_question)
        if issue_question in normalized_questions:
            reason_codes.append("duplicate_issue")
        else:
            normalized_questions.add(issue_question)
        for section in ("prevailing", "counter", "minority", "watch"):
            bullets = issue.get(section, [])
            if not isinstance(bullets, list):
                continue
            for bullet in bullets:
                if not isinstance(bullet, dict):
                    continue
                why_it_matters = str(bullet.get("why_it_matters") or "").strip()
                novelty = str(bullet.get("novelty_vs_prior_brief") or "").strip()
                text = str(bullet.get("text") or "").lower()
                claim_tokens = _normalized_tokens(text)
                watch_has_issue_anchor = section == "watch" and any(
                    marker in text for marker in ("falsification", "debate", "issue", "thesis")
                )
                if not why_it_matters:
                    reason_codes.append("empty_why_it_matters")
                if why_it_matters.lower() in TEMPLATED_WHY_IT_MATTERS:
                    reason_codes.append("templated_why_it_matters")
                if novelty not in SUPPORTED_NOVELTY_LABELS:
                    reason_codes.append("unsupported_novelty")
                if (
                    issue_tokens
                    and claim_tokens
                    and issue_tokens.isdisjoint(claim_tokens)
                    and not watch_has_issue_anchor
                ):
                    reason_codes.append("thesis_mismatch")
                if any(verb in text for verb in (" says ", " said ", " reported ", " reports ")) and any(
                    publisher in text for publisher in ("reuters", "federal reserve", "wsj", "bloomberg")
                ):
                    reason_codes.append("pseudo_analysis")

    deduped: List[str] = []
    for code in reason_codes:
        if code not in deduped:
            deduped.append(code)
    return deduped


def _normalized_tokens(text: str) -> set[str]:
    cleaned = "".join(character.lower() if character.isalnum() else " " for character in text)
    tokens = {token for token in cleaned.split() if token and token not in QUESTION_STOPWORDS}
    if "fed" in tokens:
        tokens.update({"federal", "reserve"})
    if {"federal", "reserve"}.issubset(tokens):
        tokens.add("fed")
    return tokens


if __name__ == "__main__":
    sys.exit(main())
