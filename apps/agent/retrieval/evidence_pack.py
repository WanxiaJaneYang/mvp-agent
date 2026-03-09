from __future__ import annotations

import re
from datetime import datetime, timezone
from collections.abc import Iterable, Mapping
from typing import Any


def build_evidence_pack(
    *,
    fts_rows: Iterable[Mapping[str, Any]],
    query_text: str,
    pack_size: int = 30,
) -> list[dict[str, Any]]:
    query_terms = _tokenize(query_text)
    candidate_rows = list(fts_rows)
    if not query_terms or pack_size <= 0:
        return []

    matching_rows: list[dict[str, Any]] = []
    for row in candidate_rows:
        _validate_row(row)
        keyword_score = _keyword_score(text=str(row["text"]), query_terms=query_terms)
        if keyword_score <= 0:
            continue
        matching_rows.append(
            {
                "row": row,
                "keyword_score": keyword_score,
                "published_timestamp": _published_timestamp(row),
            }
        )

    published_timestamps = [row["published_timestamp"] for row in matching_rows]
    oldest_timestamp = min(published_timestamps, default=0.0)
    newest_timestamp = max(published_timestamps, default=0.0)

    scored_rows: list[dict[str, Any]] = []
    for match in matching_rows:
        row = match["row"]
        recency_score = _recency_score(
            published_timestamp=float(match["published_timestamp"]),
            oldest_timestamp=oldest_timestamp,
            newest_timestamp=newest_timestamp,
        )
        credibility_score = _credibility_score(int(row["credibility_tier"]))
        retrieval_score = round(float(match["keyword_score"]) * 0.5 + recency_score * 0.3 + credibility_score * 0.2, 6)

        scored_rows.append(
            {
                "chunk_id": row["chunk_id"],
                "source_id": row["source_id"],
                "publisher": row["publisher"],
                "credibility_tier": row["credibility_tier"],
                "retrieval_score": retrieval_score,
                "semantic_score": None,
                "recency_score": recency_score,
                "credibility_score": credibility_score,
                "_published_timestamp": match["published_timestamp"],
            }
        )

    scored_rows.sort(
        key=lambda row: (
            -float(row["retrieval_score"]),
            -float(row["_published_timestamp"]),
            str(row["chunk_id"]),
        )
    )

    pack_rows: list[dict[str, Any]] = []
    for index, row in enumerate(scored_rows[:pack_size], start=1):
        pack_rows.append(
            {
                "chunk_id": row["chunk_id"],
                "source_id": row["source_id"],
                "publisher": row["publisher"],
                "credibility_tier": row["credibility_tier"],
                "retrieval_score": row["retrieval_score"],
                "semantic_score": row["semantic_score"],
                "recency_score": row["recency_score"],
                "credibility_score": row["credibility_score"],
                "rank_in_pack": index,
            }
        )

    return pack_rows


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def _keyword_score(*, text: str, query_terms: list[str]) -> float:
    tokens = _tokenize(text)
    return float(sum(tokens.count(term) for term in query_terms))


def _published_timestamp(row: Mapping[str, Any]) -> float:
    published_at = row.get("published_at")
    if not published_at:
        return 0.0
    try:
        return datetime.fromisoformat(str(published_at).replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
    except ValueError as exc:
        raise ValueError(f"Invalid evidence-pack row published_at value: {published_at}") from exc


def _recency_score(
    *,
    published_timestamp: float,
    oldest_timestamp: float,
    newest_timestamp: float,
) -> float:
    if newest_timestamp <= oldest_timestamp:
        return 1.0
    return round((published_timestamp - oldest_timestamp) / (newest_timestamp - oldest_timestamp), 6)


def _credibility_score(credibility_tier: int) -> float:
    scores = {
        1: 1.0,
        2: 0.8,
        3: 0.6,
        4: 0.3,
    }
    if credibility_tier not in scores:
        raise ValueError(f"Invalid evidence-pack credibility tier: {credibility_tier}")
    return scores[credibility_tier]


def _validate_row(row: Mapping[str, Any]) -> None:
    required_fields = ("chunk_id", "text", "source_id", "publisher", "credibility_tier")
    missing_fields = [field for field in required_fields if row.get(field) in (None, "")]
    if missing_fields:
        raise ValueError(f"Invalid evidence-pack row: missing {', '.join(missing_fields)}")
