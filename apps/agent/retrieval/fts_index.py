from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from apps.agent.pipeline.types import FtsRow
from apps.agent.storage.sqlite_runtime import runtime_db_path


def build_fts_rows(
    *, document: Mapping[str, Any], chunk_rows: Iterable[Mapping[str, Any]]
) -> list[FtsRow]:
    rows: list[FtsRow] = []
    for chunk_row in chunk_rows:
        _validate_chunk_row(chunk_row)
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


def search_runtime_fts_rows(
    *,
    base_dir: Path,
    query_text: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if not query_text.strip():
        return []

    connection = sqlite3.connect(runtime_db_path(base_dir=base_dir))
    try:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
              chunk_id,
              doc_id,
              publisher,
              source_id,
              published_at,
              text,
              bm25(chunk_fts) AS score
            FROM chunk_fts
            WHERE chunk_fts MATCH ?
            ORDER BY score, chunk_id
            LIMIT ?
            """,
            (_fts_query(query_text), limit),
        ).fetchall()
    finally:
        connection.close()

    return [
        {
            "chunk_id": str(row["chunk_id"]),
            "doc_id": str(row["doc_id"]),
            "publisher": str(row["publisher"]),
            "source_id": str(row["source_id"]),
            "published_at": row["published_at"],
            "text": str(row["text"]),
            "score": abs(float(row["score"])),
        }
        for row in rows
    ]


def _validate_chunk_row(chunk_row: Mapping[str, Any]) -> None:
    required_fields = ("chunk_id", "doc_id", "text")
    missing_fields = [
        field
        for field in required_fields
        if field not in chunk_row or chunk_row[field] in (None, "")
    ]
    if missing_fields:
        raise ValueError(f"Invalid chunk row for FTS indexing: missing {', '.join(missing_fields)}")


def _fts_query(query_text: str) -> str:
    terms = [term.strip() for term in query_text.split() if term.strip()]
    return " OR ".join(terms)
