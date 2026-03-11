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


class OpenAIClaimComposer(ClaimComposerProvider):
    def __init__(self, *, response_loader: Callable[[ClaimComposerInput], str | list[dict[str, Any]]] | None) -> None:
        self._response_loader = response_loader

    def compose_claims(self, *, brief_input: ClaimComposerInput) -> list[StructuredClaim]:
        if self._response_loader is None:
            raise ValueError("OpenAIClaimComposer requires a response_loader for this local runtime slice.")
        payload = self._response_loader(brief_input)
        if isinstance(payload, str):
            parsed = json.loads(payload)
        else:
            parsed = payload
        if not isinstance(parsed, list):
            raise ValueError("Claim composer output must be a list.")

        claims: list[StructuredClaim] = []
        required_fields = set(StructuredClaim.__annotations__)
        for item in parsed:
            if not isinstance(item, dict) or set(item) != required_fields:
                raise ValueError("Malformed claim composer output.")
            claims.append(_validate_structured_claim(item))
        return claims


def _validate_structured_claim(item: dict[str, Any]) -> StructuredClaim:
    if not all(
        isinstance(item.get(field), str) and item[field].strip()
        for field in ("claim_id", "issue_id", "claim_text", "confidence", "why_it_matters")
    ):
        raise ValueError("Malformed claim composer output.")
    if item.get("claim_kind") not in VALID_CLAIM_KINDS:
        raise ValueError("Malformed claim composer output.")
    if item.get("novelty_vs_prior_brief") not in VALID_NOVELTY_LABELS:
        raise ValueError("Malformed claim composer output.")
    for field in ("supporting_citation_ids", "opposing_citation_ids"):
        values = item.get(field)
        if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
            raise ValueError("Malformed claim composer output.")
    return cast(StructuredClaim, item)
