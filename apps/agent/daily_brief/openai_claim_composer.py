from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

from apps.agent.daily_brief.model_interfaces import ClaimComposerInput, ClaimComposerProvider
from apps.agent.pipeline.types import StructuredClaim

VALID_CLAIM_KINDS = {"prevailing", "counter", "minority", "watch"}
VALID_NOVELTY_LABELS = {
    "new",
    "continued",
    "reframed",
    "weakened",
    "strengthened",
    "reversed",
    "unknown",
}
REQUIRED_STRUCTURED_CLAIM_FIELDS = frozenset(StructuredClaim.__annotations__)
REQUEST_TASK = "daily_brief_claim_composer"
CLAIM_COMPOSER_SYSTEM_PROMPT = (
    "You are composing issue-centered daily brief claims from a bounded evidence set. "
    "Use only the supplied issue map, citation store, and prior context. "
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
        return self.parse_response_payload(payload=response_payload)


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
