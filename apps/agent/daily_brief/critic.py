from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from apps.agent.daily_brief.model_interfaces import CriticInput, CriticProvider
from apps.agent.pipeline.types import CriticReport, CriticStatus

PARAPHRASE_VERBS = (
    " according to ",
    " reported ",
    " reports ",
    " said ",
    " says ",
)
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
HARD_FAIL_REASON_CODES = frozenset({"empty_why_it_matters", "thesis_mismatch"})


class LocalDailyBriefCritic(CriticProvider):
    def review_brief(self, *, brief_input: CriticInput) -> CriticReport:
        return review_brief_locally(
            synthesis=brief_input["synthesis"],
            citation_store=brief_input["citation_store"],
        )


def review_brief_locally(
    *,
    synthesis: Mapping[str, Any],
    citation_store: Mapping[str, Mapping[str, Any]],
) -> CriticReport:
    reason_codes: list[str] = []
    flagged_claim_ids: set[str] = set()

    for issue in synthesis.get("issues", []):
        if not isinstance(issue, Mapping):
            continue
        issue_question = str(issue.get("issue_question") or issue.get("title") or "")
        for section, claim in _iter_issue_claims(issue):
            claim_id = _claim_id(issue, claim)

            if _is_source_by_source_paraphrase(claim=claim, citation_store=citation_store):
                _append_reason(reason_codes, "source_by_source_paraphrase")
                flagged_claim_ids.add(claim_id)

            if _has_thesis_mismatch(issue_question=issue_question, claim=claim, section=section):
                _append_reason(reason_codes, "thesis_mismatch")
                flagged_claim_ids.add(claim_id)

            if _has_empty_why_it_matters(claim):
                _append_reason(reason_codes, "empty_why_it_matters")
                flagged_claim_ids.add(claim_id)

    status: CriticStatus = "pass"
    if reason_codes:
        status = "warn"
    if any(code in HARD_FAIL_REASON_CODES for code in reason_codes):
        status = "fail"

    return {
        "status": status,
        "reason_codes": reason_codes,
        "flagged_claim_ids": sorted(flagged_claim_ids),
    }


def _iter_issue_claims(issue: Mapping[str, Any]) -> Iterable[tuple[str, Mapping[str, Any]]]:
    for section in ("prevailing", "counter", "minority", "watch"):
        claims = issue.get(section, [])
        if not isinstance(claims, list):
            continue
        for claim in claims:
            if isinstance(claim, Mapping):
                yield section, claim


def _claim_id(issue: Mapping[str, Any], claim: Mapping[str, Any]) -> str:
    raw_claim_id = claim.get("claim_id")
    if isinstance(raw_claim_id, str) and raw_claim_id.strip():
        return raw_claim_id

    issue_id = str(issue.get("issue_id") or "issue_001")
    claim_text = str(claim.get("text") or claim.get("claim_text") or "").strip()
    return f"{issue_id}:{claim_text[:32]}"


def _is_source_by_source_paraphrase(
    *,
    claim: Mapping[str, Any],
    citation_store: Mapping[str, Mapping[str, Any]],
) -> bool:
    claim_text = f" {str(claim.get('text') or claim.get('claim_text') or '').lower()} "
    citation_ids = claim.get("citation_ids") or claim.get("supporting_citation_ids") or []
    if not isinstance(citation_ids, list):
        return False

    for citation_id in citation_ids:
        citation = citation_store.get(str(citation_id))
        if not isinstance(citation, Mapping):
            continue
        publisher = str(citation.get("publisher") or "").lower().strip()
        if not publisher:
            continue
        if publisher in claim_text and any(verb in claim_text for verb in PARAPHRASE_VERBS):
            return True
    return False


def _has_thesis_mismatch(*, issue_question: str, claim: Mapping[str, Any], section: str) -> bool:
    if section == "watch":
        return False
    claim_text = str(claim.get("text") or claim.get("claim_text") or "")
    question_tokens = _normalized_tokens(issue_question)
    claim_tokens = _normalized_tokens(claim_text)
    if not question_tokens or not claim_tokens:
        return False
    return question_tokens.isdisjoint(claim_tokens)


def _has_empty_why_it_matters(claim: Mapping[str, Any]) -> bool:
    if "why_it_matters" not in claim:
        return False
    return not str(claim.get("why_it_matters") or "").strip()


def _normalized_tokens(text: str) -> set[str]:
    cleaned = "".join(character.lower() if character.isalnum() else " " for character in text)
    tokens = {token for token in cleaned.split() if token and token not in QUESTION_STOPWORDS}
    if "fed" in tokens:
        tokens.update({"federal", "reserve"})
    if {"federal", "reserve"}.issubset(tokens):
        tokens.add("fed")
    return tokens


def _append_reason(reason_codes: list[str], code: str) -> None:
    if code not in reason_codes:
        reason_codes.append(code)
