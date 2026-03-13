import sqlite3
import tempfile
import unittest
from pathlib import Path

from apps.agent.retrieval.fts_index import (
    build_fts_rows,
    persist_fts_rows,
    search_fts_rows,
    search_persisted_fts_rows,
)


class FtsIndexTests(unittest.TestCase):
    def test_builds_chunks_fts_rows_from_chunk_rows(self):
        document = {
            "doc_id": "doc_010",
            "source_id": "fed_press_releases",
            "publisher": "Federal Reserve",
            "published_at": "2026-03-10T10:00:00Z",
        }
        chunk_rows = [
            {
                "chunk_id": "doc_010_chunk_000",
                "doc_id": "doc_010",
                "chunk_index": 0,
                "text": "Rates remain restrictive",
                "token_count": 3,
                "char_start": 0,
                "char_end": 24,
                "created_at": "2026-03-10T10:05:00Z",
            }
        ]

        fts_rows = build_fts_rows(document=document, chunk_rows=chunk_rows)

        self.assertEqual(
            fts_rows,
            [
                {
                    "text": "Rates remain restrictive",
                    "doc_id": "doc_010",
                    "chunk_id": "doc_010_chunk_000",
                    "publisher": "Federal Reserve",
                    "source_id": "fed_press_releases",
                    "published_at": "2026-03-10T10:00:00Z",
                }
            ],
        )

    def test_keyword_search_orders_rows_by_term_frequency(self):
        fts_rows = [
            {
                "text": "inflation inflation rates",
                "doc_id": "doc_001",
                "chunk_id": "chunk_001",
                "publisher": "A",
                "source_id": "src_a",
                "published_at": "2026-03-10T10:00:00Z",
            },
            {
                "text": "inflation cools but rates remain high",
                "doc_id": "doc_002",
                "chunk_id": "chunk_002",
                "publisher": "B",
                "source_id": "src_b",
                "published_at": "2026-03-10T10:00:00Z",
            },
            {
                "text": "employment gains accelerate",
                "doc_id": "doc_003",
                "chunk_id": "chunk_003",
                "publisher": "C",
                "source_id": "src_c",
                "published_at": "2026-03-10T10:00:00Z",
            },
        ]

        results = search_fts_rows(fts_rows=fts_rows, query_text="inflation", limit=2)

        self.assertEqual(
            results,
            [
                {
                    "chunk_id": "chunk_001",
                    "doc_id": "doc_001",
                    "score": 2,
                    "text": "inflation inflation rates",
                },
                {
                    "chunk_id": "chunk_002",
                    "doc_id": "doc_002",
                    "score": 1,
                    "text": "inflation cools but rates remain high",
                },
            ],
        )

    def test_invalid_chunk_row_raises_value_error(self):
        document = {
            "doc_id": "doc_010",
            "source_id": "fed_press_releases",
            "publisher": "Federal Reserve",
            "published_at": "2026-03-10T10:00:00Z",
        }
        invalid_chunk_rows = [
            {
                "doc_id": "doc_010",
                "text": "Rates remain restrictive",
            }
        ]

        with self.assertRaises(ValueError):
            build_fts_rows(document=document, chunk_rows=invalid_chunk_rows)

    def test_persisted_fts_search_uses_sqlite_fts5_and_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "fts.sqlite3"
            connection = sqlite3.connect(db_path)
            try:
                persist_fts_rows(
                    connection=connection,
                    fts_rows=[
                        {
                            "text": "inflation inflation rates stay restrictive",
                            "doc_id": "doc_001",
                            "chunk_id": "chunk_001",
                            "publisher": "Federal Reserve",
                            "source_id": "src_fed",
                            "published_at": "2026-03-10T10:00:00Z",
                            "credibility_tier": 1,
                            "semantic_score": 0.2,
                        },
                        {
                            "text": "inflation cools while labor stays firm",
                            "doc_id": "doc_002",
                            "chunk_id": "chunk_002",
                            "publisher": "Reuters",
                            "source_id": "src_reuters",
                            "published_at": "2026-03-10T09:00:00Z",
                            "credibility_tier": 2,
                            "semantic_score": 0.8,
                        },
                        {
                            "text": "employment gains accelerate",
                            "doc_id": "doc_003",
                            "chunk_id": "chunk_003",
                            "publisher": "BLS",
                            "source_id": "src_bls",
                            "published_at": "2026-03-10T08:00:00Z",
                            "credibility_tier": 1,
                            "semantic_score": 0.7,
                        },
                    ],
                )

                results = search_persisted_fts_rows(
                    connection=connection,
                    query_text="inflation",
                    limit=2,
                )
            finally:
                connection.close()

        self.assertEqual([row["chunk_id"] for row in results], ["chunk_001", "chunk_002"])
        self.assertEqual(len(results), 2)
        self.assertGreater(results[0]["lexical_score"], results[1]["lexical_score"])
        self.assertEqual(results[0]["semantic_score"], 0.2)

    def test_persisted_fts_rows_preserve_existing_rows_across_batches(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "fts-incremental.sqlite3"
            connection = sqlite3.connect(db_path)
            try:
                persist_fts_rows(
                    connection=connection,
                    fts_rows=[
                        {
                            "text": "inflation outlook remains restrictive",
                            "doc_id": "doc_001",
                            "chunk_id": "chunk_001",
                            "publisher": "Federal Reserve",
                            "source_id": "src_fed",
                            "published_at": "2026-03-10T10:00:00Z",
                            "credibility_tier": 1,
                            "semantic_score": 0.2,
                        }
                    ],
                )
                persist_fts_rows(
                    connection=connection,
                    fts_rows=[
                        {
                            "text": "employment outlook remains resilient",
                            "doc_id": "doc_002",
                            "chunk_id": "chunk_002",
                            "publisher": "BLS",
                            "source_id": "src_bls",
                            "published_at": "2026-03-10T09:00:00Z",
                            "credibility_tier": 1,
                            "semantic_score": 0.7,
                        }
                    ],
                )

                results = search_persisted_fts_rows(
                    connection=connection,
                    query_text="outlook",
                    limit=5,
                )
            finally:
                connection.close()

        self.assertEqual([row["chunk_id"] for row in results], ["chunk_001", "chunk_002"])


if __name__ == "__main__":
    unittest.main()
