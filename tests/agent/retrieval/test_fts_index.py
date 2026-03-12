import tempfile
import unittest
from pathlib import Path

from apps.agent.retrieval.fts_index import build_fts_rows, search_fts_rows, search_runtime_fts_rows
from apps.agent.storage.sqlite_runtime import persist_runtime_corpus


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

    def test_runtime_fts_search_uses_persisted_sqlite_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            persist_runtime_corpus(
                base_dir=base_dir,
                source_rows=[
                    {
                        "source_id": "src_a",
                        "name": "Federal Reserve",
                        "base_url": "https://example.test/fed",
                        "source_type": "rss",
                        "credibility_tier": 1,
                        "paywall_policy": "full",
                        "fetch_interval": "daily",
                        "tags_json": "[]",
                        "enabled": 1,
                        "created_at": "2026-03-10T10:00:00Z",
                        "updated_at": "2026-03-10T10:00:00Z",
                    }
                ],
                documents=[
                    {
                        "doc_id": "doc_001",
                        "source_id": "src_a",
                        "publisher": "Federal Reserve",
                        "canonical_url": "https://example.test/fed/doc",
                        "title": "Fed note",
                        "author": None,
                        "language": "en",
                        "doc_type": "statement",
                        "published_at": "2026-03-10T10:00:00Z",
                        "fetched_at": "2026-03-10T10:05:00Z",
                        "paywall_policy": "full",
                        "metadata_only": 0,
                        "rss_snippet": "Inflation remains restrictive.",
                        "body_text": "Inflation remains restrictive.",
                        "content_hash": "hash_001",
                        "ingestion_run_id": "run_001",
                        "status": "active",
                        "created_at": "2026-03-10T10:05:00Z",
                        "updated_at": "2026-03-10T10:05:00Z",
                    }
                ],
                chunks=[
                    {
                        "chunk_id": "chunk_001",
                        "doc_id": "doc_001",
                        "chunk_index": 0,
                        "text": "Inflation remains restrictive.",
                        "token_count": 3,
                        "char_start": 0,
                        "char_end": 29,
                        "created_at": "2026-03-10T10:05:00Z",
                    }
                ],
                fts_rows=[
                    {
                        "chunk_id": "chunk_001",
                        "doc_id": "doc_001",
                        "publisher": "Federal Reserve",
                        "source_id": "src_a",
                        "published_at": "2026-03-10T10:00:00Z",
                        "text": "Inflation remains restrictive.",
                    }
                ],
            )

            results = search_runtime_fts_rows(
                base_dir=base_dir,
                query_text="inflation",
                limit=5,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], "chunk_001")
        self.assertEqual(results[0]["doc_id"], "doc_001")

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


if __name__ == "__main__":
    unittest.main()
