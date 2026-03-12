from __future__ import annotations

from collections.abc import Mapping
from typing import Any

MAX_PRIOR_ISSUES = 3
MAX_CLAIMS_PER_ISSUE = 2
ISSUE_SECTION_ORDER = ("prevailing", "counter", "minority", "watch")


def build_prior_brief_context(
    *,
    previous_synthesis: Mapping[str, Any] | None,
    previous_generated_at_utc: str | None,
) -> dict[str, Any] | None:
    if not isinstance(previous_synthesis, Mapping):
        return None

    issues = _extract_issue_contexts(previous_synthesis=previous_synthesis)
    claim_summaries = [claim for issue in issues for claim in issue["claim_summaries"]]
    citation_ids = [citation_id for issue in issues for citation_id in issue["citation_ids"]]

    return {
        "previous_generated_at_utc": previous_generated_at_utc,
        "issue_count": len(issues),
        "issue_questions": [issue["issue_question"] for issue in issues],
        "issues": issues,
        "claim_texts": claim_summaries,
        "claim_summaries": claim_summaries,
        "citation_ids": citation_ids,
    }


def _extract_issue_contexts(*, previous_synthesis: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_issues = previous_synthesis.get("issues")
    if isinstance(raw_issues, list):
        issue_contexts = [_build_issue_context(issue, index=index) for index, issue in enumerate(raw_issues, start=1)]
        return [issue for issue in issue_contexts if issue][:MAX_PRIOR_ISSUES]

    legacy_issue = _build_issue_context(
        {
            "issue_id": "prior_issue_001",
            "issue_question": "Previous daily brief",
            **{section: previous_synthesis.get(section, []) for section in ISSUE_SECTION_ORDER},
        },
        index=1,
    )
    return [] if legacy_issue is None else [legacy_issue]


def _build_issue_context(issue: Any, *, index: int) -> dict[str, Any] | None:
    if not isinstance(issue, Mapping):
        return None

    claim_summaries: list[str] = []
    citation_ids: list[str] = []
    source_refs: list[str] = []
    for bullet in _iter_issue_bullets(issue)[:MAX_CLAIMS_PER_ISSUE]:
        text = _as_non_empty_string(bullet.get("text"))
        if text is not None:
            claim_summaries.append(text)
        citation_ids.extend(_extract_citation_ids(bullet))
        source_refs.extend(_extract_source_refs(bullet))

    issue_question = (
        _as_non_empty_string(issue.get("issue_question"))
        or _as_non_empty_string(issue.get("title"))
        or f"Previous issue {index}"
    )
    return {
        "issue_id": _as_non_empty_string(issue.get("issue_id")) or f"prior_issue_{index:03d}",
        "issue_question": issue_question,
        "summary": _as_non_empty_string(issue.get("summary")),
        "claim_summaries": claim_summaries,
        "citation_ids": _dedupe_preserve_order(citation_ids),
        "source_refs": _dedupe_preserve_order(source_refs),
    }


def _iter_issue_bullets(issue: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    bullets: list[Mapping[str, Any]] = []
    for section in ISSUE_SECTION_ORDER:
        raw_bullets = issue.get(section)
        if not isinstance(raw_bullets, list):
            continue
        for bullet in raw_bullets:
            if isinstance(bullet, Mapping):
                bullets.append(bullet)
    return bullets


def _extract_citation_ids(bullet: Mapping[str, Any]) -> list[str]:
    raw_citation_ids = bullet.get("citation_ids")
    if not isinstance(raw_citation_ids, list):
        return []
    citation_ids = []
    for citation_id in raw_citation_ids:
        normalized = _as_non_empty_string(citation_id)
        if normalized is not None:
            citation_ids.append(normalized)
    return citation_ids


def _extract_source_refs(bullet: Mapping[str, Any]) -> list[str]:
    raw_evidence = bullet.get("evidence")
    if not isinstance(raw_evidence, list):
        return []
    source_refs: list[str] = []
    for evidence_item in raw_evidence:
        if not isinstance(evidence_item, Mapping):
            continue
        publisher = _as_non_empty_string(evidence_item.get("publisher"))
        published_at = _as_non_empty_string(evidence_item.get("published_at"))
        if publisher and published_at:
            source_refs.append(f"{publisher} @ {published_at}")
        elif publisher:
            source_refs.append(publisher)
        elif published_at:
            source_refs.append(published_at)
    return source_refs


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _as_non_empty_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None
