from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from apps.agent.pipeline.types import (
    ClaimDelta,
    DailyBriefBullet,
    DailyBriefNoveltyLabel,
    StructuredClaim,
)

CHANGED_LABELS = {"new", "reframed", "weakened", "strengthened", "reversed"}


def build_claim_deltas(
    *,
    structured_claims: Iterable[StructuredClaim],
    prior_brief_context: Mapping[str, Any] | None,
) -> list[ClaimDelta]:
    prior_claims = []
    if isinstance(prior_brief_context, Mapping):
        prior_claims = [
            str(value)
            for value in prior_brief_context.get("claim_summaries", [])
            if isinstance(value, str)
        ]

    deltas: list[ClaimDelta] = []
    for claim in structured_claims:
        best_match, overlap = _best_prior_match(
            claim_text=str(claim["claim_text"]),
            prior_claims=prior_claims,
        )
        novelty: DailyBriefNoveltyLabel = claim.get("novelty_vs_prior_brief", "unknown")
        if novelty == "unknown":
            novelty = "continued" if overlap >= 0.55 else "new"
        deltas.append(
            ClaimDelta(
                claim_id=str(claim["claim_id"]),
                prior_claim_ref=best_match,
                novelty_label=novelty,
                delta_explanation=_delta_explanation(
                    novelty_label=novelty,
                    claim_text=str(claim["claim_text"]),
                    prior_claim_ref=best_match,
                ),
                supporting_prior_overlap={
                    "citation_overlap": round(overlap, 2),
                    "thesis_overlap": _overlap_label(overlap),
                },
            )
        )
    return deltas


def build_changed_section_from_deltas(
    *,
    structured_claims: Iterable[StructuredClaim],
    claim_deltas: Iterable[ClaimDelta],
    limit: int = 3,
) -> list[DailyBriefBullet]:
    claims_by_id = {str(claim["claim_id"]): claim for claim in structured_claims}
    changed: list[DailyBriefBullet] = []
    for delta in claim_deltas:
        novelty_label = delta["novelty_label"]
        if novelty_label not in CHANGED_LABELS:
            continue
        claim = claims_by_id.get(str(delta["claim_id"]))
        if claim is None:
            continue
        changed.append(
            DailyBriefBullet(
                claim_id=str(claim["claim_id"]),
                claim_kind=claim["claim_kind"],
                text=f"{novelty_label.capitalize()}: {claim['claim_text']}",
                citation_ids=[str(citation_id) for citation_id in claim.get("supporting_citation_ids", [])],
                confidence_label=str(claim.get("confidence", "medium")),
                why_it_matters=str(claim.get("why_it_matters") or ""),
                novelty_vs_prior_brief=novelty_label,
                delta_label=novelty_label,
                delta_explanation=str(delta["delta_explanation"]),
            )
        )
        if len(changed) >= limit:
            break
    return changed


def _best_prior_match(*, claim_text: str, prior_claims: Iterable[str]) -> tuple[str | None, float]:
    best_match: str | None = None
    best_overlap = 0.0
    claim_tokens = _tokens(claim_text)
    for prior_claim in prior_claims:
        overlap = _jaccard(claim_tokens, _tokens(prior_claim))
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = prior_claim
    return best_match, best_overlap


def _delta_explanation(*, novelty_label: str, claim_text: str, prior_claim_ref: str | None) -> str:
    if prior_claim_ref is None:
        return f"{novelty_label.capitalize()} claim with no close prior analogue: {claim_text}"
    return (
        f"{novelty_label.capitalize()} versus prior brief. "
        f"Closest prior claim: {prior_claim_ref}"
    )


def _overlap_label(overlap: float) -> str:
    if overlap >= 0.65:
        return "high"
    if overlap >= 0.35:
        return "medium"
    return "low"


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    return len(left & right) / len(left | right)
