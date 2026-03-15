from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast

from apps.agent.daily_brief.model_interfaces import ClaimComposerInput, ClaimComposerProvider
from apps.agent.pipeline.types import StructuredClaim

VALID_CLAIM_KINDS = {"prevailing", "counter", "minority", "watch"}
CLAIM_KIND_TO_ISSUE_FIELD = {
    "prevailing": "supporting_evidence_ids",
    "counter": "opposing_evidence_ids",
    "minority": "minority_evidence_ids",
    "watch": "watch_evidence_ids",
}
CLAIM_KIND_TO_OPPOSING_FIELD = {
    "prevailing": "opposing_evidence_ids",
    "counter": "supporting_evidence_ids",
    "minority": "supporting_evidence_ids",
    "watch": "supporting_evidence_ids",
}
VALID_NOVELTY_LABELS = {
    "new",
    "continued",
    "reframed",
    "weakened",
    "strengthened",
    "reversed",
    "unknown",
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
TEMPLATED_WHY_IT_MATTERS = frozenset(
    {
        "investors should watch this closely.",
        "investors should watch this closely",
        "this could move markets.",
        "this could move markets",
    }
)
REQUIRED_STRUCTURED_CLAIM_FIELDS = frozenset(StructuredClaim.__annotations__)
REQUEST_TASK = "daily_brief_claim_composer"
CLAIM_COMPOSER_SYSTEM_PROMPT = (
    "You are composing issue-centered daily brief claims from a bounded evidence set. "
    "Use only the supplied issue map, issue-local citation scopes, citation store, and prior context. "
    "Keep supporting citations aligned to the matching issue bucket and never borrow citations across issues. "
    "Return strict JSON matching the structured-claim schema."
)
STRUCTURED_CLAIMS_JSON_SCHEMA: dict[str, Any] = {
    "name": "structured_claims_list",
    "strict": True,
    "schema": {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": sorted(REQUIRED_STRUCTURED_CLAIM_FIELDS),
            "properties": {
                "claim_id": {"type": "string"},
                "issue_id": {"type": "string"},
                "claim_kind": {"type": "string", "enum": sorted(VALID_CLAIM_KINDS)},
                "claim_text": {"type": "string"},
                "supporting_citation_ids": {"type": "array", "items": {"type": "string"}},
                "opposing_citation_ids": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string"},
                "novelty_vs_prior_brief": {"type": "string", "enum": sorted(VALID_NOVELTY_LABELS)},
                "why_it_matters": {"type": "string"},
            },
        },
    },
}


class OpenAIClaimComposer(ClaimComposerProvider):
    def __init__(self, *, response_loader: Callable[[ClaimComposerInput], str | list[dict[str, Any]]] | None) -> None:
        self._response_loader = response_loader

    def build_request_payload(self, *, brief_input: ClaimComposerInput) -> dict[str, Any]:
        return {
            "task": REQUEST_TASK,
            "run_id": str(brief_input["run_id"]),
            "generated_at_utc": str(brief_input["generated_at_utc"]),
            "response_format": {"type": "json_schema", "json_schema": STRUCTURED_CLAIMS_JSON_SCHEMA},
            "messages": [
                {"role": "system", "content": CLAIM_COMPOSER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Compose structured prevailing, counter, minority, and watch claims "
                        "for each issue. Return only strict JSON matching the schema."
                    ),
                },
            ],
            "input": {
                "issue_map": [dict(issue) for issue in brief_input["issue_map"]],
                "issue_citation_scopes": _build_issue_citation_scopes(
                    issue_map=brief_input["issue_map"],
                    citation_store=brief_input["citation_store"],
                ),
                "citation_store": {
                    str(citation_id): dict(citation_payload)
                    for citation_id, citation_payload in brief_input["citation_store"].items()
                },
                "prior_brief_context": (
                    None
                    if brief_input["prior_brief_context"] is None
                    else dict(brief_input["prior_brief_context"])
                ),
            },
        }

    def parse_response_payload(self, *, payload: str | list[dict[str, Any]]) -> list[StructuredClaim]:
        parsed = json.loads(payload) if isinstance(payload, str) else payload
        if not isinstance(parsed, list):
            raise ValueError("Claim composer output must be a list.")

        claims: list[StructuredClaim] = []
        for item in parsed:
            if not isinstance(item, dict) or set(item) != REQUIRED_STRUCTURED_CLAIM_FIELDS:
                raise ValueError("Malformed claim composer output.")
            claims.append(_validate_structured_claim(item))
        return claims

    def compose_claims(self, *, brief_input: ClaimComposerInput) -> list[StructuredClaim]:
        if self._response_loader is None:
            raise ValueError("OpenAIClaimComposer requires a response_loader for this local runtime slice.")
        request_payload = self.build_request_payload(brief_input=brief_input)
        response_payload = self._response_loader(cast(ClaimComposerInput, request_payload))
        claims = self.parse_response_payload(payload=response_payload)
        _validate_claim_bindings(claims=claims, brief_input=brief_input)
        return claims


def _build_issue_citation_scopes(
    *,
    issue_map: Sequence[Mapping[str, Any]],
    citation_store: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    allowlists = _issue_citation_allowlists(issue_map=issue_map, citation_store=citation_store)
    scopes: list[dict[str, Any]] = []
    for issue in issue_map:
        issue_id = str(issue.get("issue_id") or "")
        if not issue_id or issue_id not in allowlists:
            continue
        issue_scope = allowlists[issue_id]
        scopes.append(
            {
                "issue_id": issue_id,
                "supporting_citation_ids": sorted(issue_scope["supporting_evidence_ids"]),
                "opposing_citation_ids": sorted(issue_scope["opposing_evidence_ids"]),
                "minority_citation_ids": sorted(issue_scope["minority_evidence_ids"]),
                "watch_citation_ids": sorted(issue_scope["watch_evidence_ids"]),
            }
        )
    return scopes


def _validate_claim_bindings(*, claims: list[StructuredClaim], brief_input: ClaimComposerInput) -> None:
    issue_citation_allowlists = _issue_citation_allowlists(
        issue_map=brief_input["issue_map"],
        citation_store=brief_input["citation_store"],
    )
    issues_by_id = {
        str(issue.get("issue_id") or ""): issue
        for issue in brief_input["issue_map"]
        if isinstance(issue, Mapping) and str(issue.get("issue_id") or "")
    }
    for claim in claims:
        issue_id = str(claim["issue_id"])
        issue_scope = issue_citation_allowlists.get(issue_id)
        if issue_scope is None:
            raise ValueError("Malformed claim composer output.")
        support_field = CLAIM_KIND_TO_ISSUE_FIELD[str(claim["claim_kind"])]
        opposing_field = CLAIM_KIND_TO_OPPOSING_FIELD[str(claim["claim_kind"])]
        if any(citation_id not in issue_scope[support_field] for citation_id in claim["supporting_citation_ids"]):
            raise ValueError("Malformed claim composer output.")
        if any(citation_id not in issue_scope[opposing_field] for citation_id in claim["opposing_citation_ids"]):
            raise ValueError("Malformed claim composer output.")
        issue = issues_by_id.get(issue_id)
        if issue is None:
            raise ValueError("Malformed claim composer output.")
        _validate_claim_semantics(claim=claim, issue=issue)


def _issue_citation_allowlists(
    *,
    issue_map: Sequence[Mapping[str, Any]],
    citation_store: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, set[str]]]:
    citations_by_chunk_id: dict[str, set[str]] = {}
    for citation_id, citation_payload in citation_store.items():
        if not isinstance(citation_payload, Mapping) or citation_payload.get("chunk_id") is None:
            continue
        citations_by_chunk_id.setdefault(str(citation_payload["chunk_id"]), set()).add(str(citation_id))

    issue_citation_allowlists: dict[str, dict[str, set[str]]] = {}
    for issue in issue_map:
        issue_id = str(issue.get("issue_id") or "")
        if not issue_id:
            continue
        issue_scope: dict[str, set[str]] = {}
        all_citation_ids: set[str] = set()
        for issue_field in CLAIM_KIND_TO_ISSUE_FIELD.values():
            citation_ids = _citation_ids_for_issue_field(
                values=issue.get(issue_field),
                citations_by_chunk_id=citations_by_chunk_id,
            )
            issue_scope[issue_field] = citation_ids
            all_citation_ids.update(citation_ids)
        issue_scope["all_citation_ids"] = all_citation_ids
        issue_citation_allowlists[issue_id] = issue_scope
    return issue_citation_allowlists


def _citation_ids_for_issue_field(
    *,
    values: Any,
    citations_by_chunk_id: Mapping[str, set[str]],
) -> set[str]:
    if not isinstance(values, list):
        return set()
    citation_ids: set[str] = set()
    for chunk_id in values:
        if not isinstance(chunk_id, str) or not chunk_id:
            continue
        citation_ids.update(citations_by_chunk_id.get(chunk_id, set()))
    return citation_ids


def _validate_structured_claim(item: dict[str, Any]) -> StructuredClaim:
    normalized_text_fields: dict[str, str] = {}
    for field in ("claim_id", "issue_id", "claim_text", "confidence", "why_it_matters"):
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Malformed claim composer output.")
        normalized_text_fields[field] = value.strip()
    claim_kind = item.get("claim_kind")
    if claim_kind not in VALID_CLAIM_KINDS:
        raise ValueError("Malformed claim composer output.")
    novelty = item.get("novelty_vs_prior_brief")
    if novelty not in VALID_NOVELTY_LABELS:
        raise ValueError("Malformed claim composer output.")
    normalized_citation_fields: dict[str, list[str]] = {}
    for field in ("supporting_citation_ids", "opposing_citation_ids"):
        values = item.get(field)
        if not isinstance(values, list):
            raise ValueError("Malformed claim composer output.")
        normalized_values = []
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Malformed claim composer output.")
            normalized_values.append(value.strip())
        if field == "supporting_citation_ids" and not normalized_values:
            raise ValueError("Malformed claim composer output.")
        normalized_citation_fields[field] = normalized_values
    return StructuredClaim(
        claim_id=normalized_text_fields["claim_id"],
        issue_id=normalized_text_fields["issue_id"],
        claim_kind=claim_kind,
        claim_text=normalized_text_fields["claim_text"],
        supporting_citation_ids=normalized_citation_fields["supporting_citation_ids"],
        opposing_citation_ids=normalized_citation_fields["opposing_citation_ids"],
        confidence=normalized_text_fields["confidence"],
        novelty_vs_prior_brief=novelty,
        why_it_matters=normalized_text_fields["why_it_matters"],
    )


def _validate_claim_semantics(*, claim: StructuredClaim, issue: Mapping[str, Any]) -> None:
    claim_text = str(claim["claim_text"])
    normalized_claim_text = claim_text.lower()
    issue_tokens = _normalized_tokens(
        " ".join(
            (
                str(issue.get("issue_question") or ""),
                str(issue.get("thesis_hint") or ""),
            )
        )
    )
    claim_tokens = _normalized_tokens(claim_text)
    watch_has_issue_anchor = str(claim["claim_kind"]) == "watch" and any(
        marker in normalized_claim_text for marker in ("falsification", "debate", "issue", "thesis")
    )
    if issue_tokens and claim_tokens and issue_tokens.isdisjoint(claim_tokens) and not watch_has_issue_anchor:
        raise ValueError("Malformed claim composer output.")
    if str(claim["why_it_matters"]).strip().lower() in TEMPLATED_WHY_IT_MATTERS:
        raise ValueError("Malformed claim composer output.")


def _normalized_tokens(value: str) -> set[str]:
    cleaned = "".join(character.lower() if character.isalnum() else " " for character in value)
    tokens = {token for token in cleaned.split() if token and token not in QUESTION_STOPWORDS}
    if "fed" in tokens:
        tokens.update({"federal", "reserve"})
    if {"federal", "reserve"}.issubset(tokens):
        tokens.add("fed")
    return tokens
