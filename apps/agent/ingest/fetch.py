from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any


def plan_fetch_items(
    *,
    sources: Iterable[Mapping[str, Any]],
    candidate_payloads: Mapping[str, Sequence[Mapping[str, Any]]],
    default_per_source_cap: int = 10,
    global_cap: int = 200,
) -> list[dict[str, Any]]:
    planned: list[dict[str, Any]] = []
    for source in sources:
        source_id = str(source["id"])
        per_source_cap = int(source.get("per_fetch_cap", default_per_source_cap))
        source_candidates = candidate_payloads.get(source_id, ())
        for payload in source_candidates[:per_source_cap]:
            if len(planned) >= global_cap:
                return planned
            planned.append(
                {
                    "source_id": source_id,
                    "payload": dict(payload),
                }
            )
    return planned
