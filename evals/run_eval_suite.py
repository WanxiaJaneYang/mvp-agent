from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.agent.daily_brief.runner import (  # noqa: E402
    DEFAULT_FIXTURE_PATH,
    run_daily_brief,
    run_fixture_daily_brief,
)
from apps.agent.daily_brief.semantic_checks import (  # noqa: E402
    TEMPLATED_WHY_IT_MATTERS,
    has_watch_issue_anchor,
    normalized_issue_tokens,
)
from apps.agent.pipeline.stage8_validation import run_stage8_citation_validation  # noqa: E402
from apps.agent.retrieval.evidence_pack import build_evidence_pack  # noqa: E402
from apps.agent.synthesis.postprocess import CORE_SECTIONS, finalize_validation_outcome  # noqa: E402

SUPPORTED_NOVELTY_LABELS = {"new", "continued", "reframed", "weakened", "strengthened", "reversed"}


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


def _run_daily_brief_stage_case(case: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    run_mode = str(case.get("run_mode") or "fixture")
    generated_at_utc = str(case.get("generated_at_utc") or "2026-03-10T16:00:00Z")
    expected = case.get("expected", {})

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        fixture_path, payloads = _resolve_fixture_payloads(case=case, temp_dir=temp_dir)
        issue_planner, claim_composer, critic = _build_stage_providers(case=case)

        if run_mode == "fixture_live_parity":
            fixture_result = run_fixture_daily_brief(
                base_dir=temp_dir / "fixture",
                fixture_path=fixture_path,
                run_id=str(case.get("run_id") or f"{case.get('id', 'daily_brief_stage').lower()}_fixture"),
                generated_at_utc=generated_at_utc,
                issue_planner=issue_planner,
                claim_composer=claim_composer,
                critic=critic,
            )
            with patch("apps.agent.daily_brief.runner.fetch_live_payloads_for_source") as live_fetch_mock:
                live_fetch_mock.side_effect = (
                    lambda *, source, fetched_at_utc: [dict(item) for item in payloads.get(str(source["id"]), [])]
                )
                live_result = run_daily_brief(
                    base_dir=temp_dir / "live",
                    run_id=str(case.get("run_id") or f"{case.get('id', 'daily_brief_stage').lower()}_live"),
                    generated_at_utc=generated_at_utc,
                    issue_planner=issue_planner,
                    claim_composer=claim_composer,
                    critic=critic,
                )

            for field in expected.get("parity_fields", []):
                if fixture_result.get(field) != live_result.get(field):
                    errors.append(
                        f"expected fixture/live parity for {field}, got {fixture_result.get(field)} vs {live_result.get(field)}"
                    )
            return errors

        if run_mode != "fixture":
            return [f"unsupported run_mode: {run_mode}"]

        result = run_fixture_daily_brief(
            base_dir=temp_dir / "fixture",
            fixture_path=fixture_path,
            run_id=str(case.get("run_id") or case.get("id") or "daily_brief_stage"),
            generated_at_utc=generated_at_utc,
            issue_planner=issue_planner,
            claim_composer=claim_composer,
            critic=critic,
        )
        errors.extend(_validate_daily_brief_stage_result(result=result, expected=expected))

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
        if case_type == "daily_brief_stage":
            return [f"{case_id}: {error}" for error in _run_daily_brief_stage_case(case)]
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
        issue_tokens = normalized_issue_tokens(issue_question)
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
                claim_tokens = normalized_issue_tokens(text)
                watch_has_issue_anchor = section == "watch" and has_watch_issue_anchor(text)
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


def _resolve_fixture_payloads(*, case: Dict[str, Any], temp_dir: Path) -> tuple[Path, dict[str, list[dict[str, Any]]]]:
    inline_payloads = case.get("fixture_payloads")
    if isinstance(inline_payloads, dict):
        fixture_path = temp_dir / "fixture_payloads.json"
        fixture_path.write_text(json.dumps(inline_payloads), encoding="utf-8")
        return fixture_path, {str(key): [dict(item) for item in value] for key, value in inline_payloads.items()}

    fixture_path_value = case.get("fixture_path")
    fixture_path = ROOT / str(fixture_path_value) if isinstance(fixture_path_value, str) else DEFAULT_FIXTURE_PATH
    payloads = json.loads(fixture_path.read_text(encoding="utf-8"))
    return fixture_path, {str(key): [dict(item) for item in value] for key, value in payloads.items()}


def _build_stage_providers(case: Dict[str, Any]) -> tuple[Any | None, Any | None, Any | None]:
    provider_case = case.get("providers")
    if not isinstance(provider_case, dict):
        return None, None, None

    issue_specs = provider_case.get("issues", [])
    claim_specs = provider_case.get("claims", [])
    critic_spec = provider_case.get("critic", {})

    class _CaseIssuePlanner:
        def plan_issues(self, *, brief_input):
            scopes = brief_input["issue_evidence_scopes"]
            issue_map = []
            for index, spec in enumerate(issue_specs if isinstance(issue_specs, list) else []):
                scope_index = int(spec.get("scope_index", index))
                if scope_index >= len(scopes):
                    raise ValueError(f"issue scope index {scope_index} out of range for daily_brief_stage case")
                scope = scopes[scope_index]
                issue_map.append(
                    {
                        "issue_id": str(spec.get("issue_id") or f"issue_{index + 1:03d}"),
                        "issue_question": str(spec["issue_question"]),
                        "thesis_hint": str(spec.get("thesis_hint") or spec["issue_question"]),
                        "supporting_evidence_ids": list(scope.get("primary_chunk_ids", [])),
                        "opposing_evidence_ids": list(scope.get("opposing_chunk_ids", [])),
                        "minority_evidence_ids": list(scope.get("minority_chunk_ids", [])),
                        "watch_evidence_ids": list(scope.get("watch_chunk_ids", [])),
                    }
                )
            return issue_map

    class _CaseClaimComposer:
        def compose_claims(self, *, brief_input):
            issue_map = brief_input["issue_map"]
            citation_store = brief_input["citation_store"]
            citation_ids_by_source: dict[str, list[str]] = {}
            for citation_id, entry in citation_store.items():
                source_id = str(entry.get("source_id") or "")
                if source_id:
                    citation_ids_by_source.setdefault(source_id, []).append(str(citation_id))

            claims = []
            for index, spec in enumerate(claim_specs if isinstance(claim_specs, list) else []):
                issue_index = int(spec.get("issue_index", 0))
                if issue_index >= len(issue_map):
                    raise ValueError(f"issue index {issue_index} out of range for daily_brief_stage claim")
                source_id = str(spec["citation_source_id"])
                citation_ids = citation_ids_by_source.get(source_id, [])
                if not citation_ids:
                    raise ValueError(f"no citations found for source_id={source_id}")
                issue_id = str(issue_map[issue_index]["issue_id"])
                claims.append(
                    {
                        "claim_id": str(spec.get("claim_id") or f"{issue_id}_{spec['claim_kind']}_{index + 1:03d}"),
                        "issue_id": issue_id,
                        "claim_kind": str(spec["claim_kind"]),
                        "claim_text": str(spec["text"]),
                        "supporting_citation_ids": [citation_ids[0]],
                        "opposing_citation_ids": list(spec.get("opposing_citation_ids", [])),
                        "confidence": str(spec.get("confidence") or "medium"),
                        "novelty_vs_prior_brief": str(spec.get("novelty_vs_prior_brief") or "continued"),
                        "why_it_matters": str(spec.get("why_it_matters") or "This matters for the active issue."),
                    }
                )
            return claims

    class _CaseCritic:
        def review_brief(self, *, brief_input):
            if not isinstance(critic_spec, dict):
                return {"status": "pass", "reason_codes": [], "flagged_claim_ids": []}
            return {
                "status": str(critic_spec.get("status") or "pass"),
                "reason_codes": list(critic_spec.get("reason_codes", [])),
                "flagged_claim_ids": list(critic_spec.get("flagged_claim_ids", [])),
            }

    critic = _CaseCritic() if isinstance(critic_spec, dict) and critic_spec else None
    return _CaseIssuePlanner(), _CaseClaimComposer(), critic


def _validate_daily_brief_stage_result(*, result: Dict[str, Any], expected: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    artifact_dir_value = result.get("artifact_dir")
    if not artifact_dir_value:
        errors.append("missing artifact_dir in daily_brief_stage result")
        return errors
    artifact_dir = Path(str(artifact_dir_value))
    html_path_value = result.get("html_path")
    html_path = Path(str(html_path_value)) if html_path_value else None
    html = html_path.read_text(encoding="utf-8") if html_path and html_path.exists() else ""

    expected_status = expected.get("status")
    if expected_status is not None and result.get("status") != expected_status:
        errors.append(f"expected status={expected_status}, got {result.get('status')}")

    expected_publish_decision = expected.get("publish_decision")
    if expected_publish_decision is not None and result.get("publish_decision") != expected_publish_decision:
        errors.append(
            f"expected publish_decision={expected_publish_decision}, got {result.get('publish_decision')}"
        )

    for relative_path in expected.get("artifact_paths", []):
        if not (artifact_dir / str(relative_path)).exists():
            errors.append(f"missing artifact: {relative_path}")

    corpus_summary_path = artifact_dir / "corpus_summary.json"
    corpus_summary_expectations = expected.get("corpus_summary_contains", [])
    if corpus_summary_expectations:
        if not corpus_summary_path.exists():
            errors.append("missing artifact required for corpus_summary expectations: corpus_summary.json")
        else:
            corpus_summary = json.loads(corpus_summary_path.read_text(encoding="utf-8"))
            for needle in corpus_summary_expectations:
                if not any(str(needle) in str(item) for item in corpus_summary):
                    errors.append(f"expected corpus_summary to contain {needle!r}")

    brief_plan_path = artifact_dir / "brief_plan.json"
    brief_thesis_expectations = expected.get("brief_thesis_contains", [])
    if brief_thesis_expectations:
        if not brief_plan_path.exists():
            errors.append("missing artifact required for brief_thesis expectations: brief_plan.json")
        else:
            brief_plan = json.loads(brief_plan_path.read_text(encoding="utf-8"))
            brief_thesis = str(brief_plan.get("brief_thesis") or "")
            for needle in brief_thesis_expectations:
                if str(needle) not in brief_thesis:
                    errors.append(f"expected brief_thesis to contain {needle!r}")

    issue_scopes_path = artifact_dir / "issue_evidence_scopes.json"
    minimum_scope_count = expected.get("issue_scope_count_at_least")
    if minimum_scope_count is not None:
        if not issue_scopes_path.exists():
            errors.append("missing artifact required for issue_scope_count expectations: issue_evidence_scopes.json")
        else:
            issue_scopes = json.loads(issue_scopes_path.read_text(encoding="utf-8"))
            if len(issue_scopes) < int(minimum_scope_count):
                errors.append(f"expected issue_scope_count>={minimum_scope_count}, got {len(issue_scopes)}")

    issue_map_path = artifact_dir / "issue_map.json"
    issue_map_count = expected.get("issue_map_count")
    if issue_map_count is not None:
        if not issue_map_path.exists():
            errors.append("missing artifact required for issue_map_count expectations: issue_map.json")
        else:
            issue_map = json.loads(issue_map_path.read_text(encoding="utf-8"))
            if len(issue_map) != int(issue_map_count):
                errors.append(f"expected issue_map_count={issue_map_count}, got {len(issue_map)}")

    claim_objects_path = artifact_dir / "claim_objects.json"
    claim_count = expected.get("claim_count")
    if claim_count is not None:
        if not claim_objects_path.exists():
            errors.append("missing artifact required for claim_count expectations: claim_objects.json")
        else:
            claim_objects = json.loads(claim_objects_path.read_text(encoding="utf-8"))
            if len(claim_objects) != int(claim_count):
                errors.append(f"expected claim_count={claim_count}, got {len(claim_objects)}")

    for needle in expected.get("html_contains", []):
        if str(needle) not in html:
            errors.append(f"expected html to contain {needle!r}")
    for needle in expected.get("html_not_contains", []):
        if str(needle) in html:
            errors.append(f"expected html to exclude {needle!r}")

    return errors


if __name__ == "__main__":
    sys.exit(main())
