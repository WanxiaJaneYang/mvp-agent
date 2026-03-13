from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from typing import Any

from apps.agent.pipeline.types import FtsRow

FTS_TABLE_NAME = "chunks_fts"
FTS_LOOKUP_TABLE_NAME = "chunks_fts_lookup"


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


def persist_fts_rows(
    *,
    connection: sqlite3.Connection,
    fts_rows: Iterable[Mapping[str, Any]],
) -> None:
    connection.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE_NAME}
        USING fts5(
          chunk_id UNINDEXED,
          doc_id UNINDEXED,
          publisher UNINDEXED,
          source_id UNINDEXED,
          published_at UNINDEXED,
          credibility_tier UNINDEXED,
          semantic_score UNINDEXED,
          text
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {FTS_LOOKUP_TABLE_NAME} (
          chunk_id TEXT PRIMARY KEY,
          fts_rowid INTEGER NOT NULL
        )
        """
    )

    for row in fts_rows:
        _validate_persistable_row(row)
        chunk_id = str(row["chunk_id"])
        existing_row = connection.execute(
            f"SELECT fts_rowid FROM {FTS_LOOKUP_TABLE_NAME} WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        if existing_row is not None:
            stored_rowid = existing_row[0]
            if stored_rowid is not None:
                connection.execute(
                    f"DELETE FROM {FTS_TABLE_NAME} WHERE rowid = ?",
                    (int(stored_rowid),),
                )
        cursor = connection.execute(
            f"""
            INSERT INTO {FTS_TABLE_NAME} (
              chunk_id, doc_id, publisher, source_id, published_at,
              credibility_tier, semantic_score, text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk_id,
                str(row["doc_id"]),
                str(row["publisher"]),
                str(row["source_id"]),
                row.get("published_at"),
                int(row.get("credibility_tier", 4) or 4),
                _optional_float(row.get("semantic_score")),
                str(row["text"]),
            ),
        )
        inserted_rowid = cursor.lastrowid
        if inserted_rowid is None:
            raise RuntimeError("SQLite FTS insert did not return a rowid for persisted retrieval state.")
        connection.execute(
            f"""
            INSERT INTO {FTS_LOOKUP_TABLE_NAME} (chunk_id, fts_rowid)
            VALUES (?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET fts_rowid = excluded.fts_rowid
            """,
            (chunk_id, int(inserted_rowid)),
        )
    connection.commit()


def search_persisted_fts_rows(
    *,
    connection: sqlite3.Connection,
    query_text: str,
    limit: int | None = 5,
) -> list[dict[str, Any]]:
    normalized_query = query_text.strip()
    if not normalized_query or (limit is not None and limit <= 0):
        return []

    query = f"""
        SELECT
          chunk_id,
          doc_id,
          publisher,
          source_id,
          published_at,
          credibility_tier,
          semantic_score,
          text,
          bm25({FTS_TABLE_NAME}) AS bm25_score
        FROM {FTS_TABLE_NAME}
        WHERE {FTS_TABLE_NAME} MATCH ?
        ORDER BY bm25_score ASC, chunk_id ASC
        """
    parameters: tuple[Any, ...]
    if limit is None:
        parameters = (normalized_query,)
    else:
        query += "\n        LIMIT ?"
        parameters = (normalized_query, limit)
    cursor = connection.execute(query, parameters)
    columns = [column[0] for column in cursor.description or []]
    rows = [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
    lexical_scores = _normalized_lexical_scores(rows)
    persisted_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        persisted_rows.append(
            {
                "chunk_id": row["chunk_id"],
                "doc_id": row["doc_id"],
                "publisher": row["publisher"],
                "source_id": row["source_id"],
                "published_at": row["published_at"],
                "credibility_tier": int(row["credibility_tier"]),
                "semantic_score": _optional_float(row["semantic_score"]),
                "lexical_score": lexical_scores[index],
                "text": row["text"],
            }
        )
    return persisted_rows


def _validate_chunk_row(chunk_row: Mapping[str, Any]) -> None:
    required_fields = ("chunk_id", "doc_id", "text")
    missing_fields = [
        field
        for field in required_fields
        if field not in chunk_row or chunk_row[field] in (None, "")
    ]
    if missing_fields:
        raise ValueError(f"Invalid chunk row for FTS indexing: missing {', '.join(missing_fields)}")


def _validate_persistable_row(row: Mapping[str, Any]) -> None:
    required_fields = ("chunk_id", "doc_id", "text", "source_id", "publisher")
    missing_fields = [field for field in required_fields if row.get(field) in (None, "")]
    if missing_fields:
        raise ValueError(
            f"Invalid persisted FTS row for indexing: missing {', '.join(missing_fields)}"
        )


def _normalized_lexical_scores(rows: list[dict[str, Any]]) -> list[float]:
    if not rows:
        return []
    raw_scores = [float(row["bm25_score"]) for row in rows]
    best_score = min(raw_scores)
    worst_score = max(raw_scores)
    if worst_score == best_score:
        return [1.0 for _row in rows]
    return [round((worst_score - score) / (worst_score - best_score), 6) for score in raw_scores]


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
