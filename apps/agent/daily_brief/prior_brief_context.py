from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_prior_brief_context(
    *,
    previous_synthesis: Mapping[str, Any] | None,
    previous_generated_at_utc: str | None,
) -> dict[str, Any] | None:
    if not isinstance(previous_synthesis, Mapping):
        return None

    claim_summaries: list[str] = []
    citation_ids: list[str] = []
    for section in ("prevailing", "counter", "minority", "watch"):
        bullets = previous_synthesis.get(section, [])
        if not isinstance(bullets, list):
            continue
        for bullet in bullets[:1]:
            if not isinstance(bullet, Mapping):
                continue
            text = str(bullet.get("text", "")).strip()
            if text:
                claim_summaries.append(text)
            current_citation_ids = bullet.get("citation_ids", [])
            if isinstance(current_citation_ids, list):
                for citation_id in current_citation_ids:
                    citation_ids.append(str(citation_id))

    return {
        "previous_generated_at_utc": previous_generated_at_utc,
        "claim_summaries": claim_summaries,
        "citation_ids": citation_ids,
    }
