from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def build_fts_rows(*, document: Mapping[str, Any], chunk_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk_row in chunk_rows:
        rows.append(
            {
                "text": chunk_row["text"],
                "doc_id": chunk_row["doc_id"],
                "chunk_id": chunk_row["chunk_id"],
                "publisher": document["publisher"],
                "source_id": document["source_id"],
                "published_at": document.get("published_at"),
            }
        )
    return rows


def search_fts_rows(
    *,
    fts_rows: Iterable[Mapping[str, Any]],
    query_text: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    normalized_query = query_text.lower()
    matches: list[dict[str, Any]] = []
    for row in fts_rows:
        text = str(row["text"])
        score = text.lower().split().count(normalized_query)
        if score <= 0:
            continue
        matches.append(
            {
                "chunk_id": row["chunk_id"],
                "doc_id": row["doc_id"],
                "score": score,
                "text": text,
            }
        )

    matches.sort(key=lambda item: (-item["score"], item["chunk_id"]))
    return matches[:limit]
