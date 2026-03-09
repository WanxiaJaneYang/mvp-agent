import unittest

from apps.agent.retrieval.chunker import build_chunk_rows, chunk_document


class ChunkDocumentTests(unittest.TestCase):
    def test_splits_full_text_document_into_stable_ordered_chunks(self):
        document = {
            "doc_id": "doc_001",
            "source_id": "fed_press_releases",
            "publisher": "Federal Reserve",
            "published_at": "2026-03-10T08:00:00Z",
            "fetched_at": "2026-03-10T08:05:00Z",
            "metadata_only": 0,
            "body_text": (
                "Alpha beta gamma delta epsilon zeta eta theta "
                "iota kappa lambda mu nu xi omicron pi rho sigma tau."
            ),
        }

        chunks = chunk_document(document=document, max_chars=32)

        self.assertEqual(
            chunks,
            [
                {
                    "chunk_index": 0,
                    "text": "Alpha beta gamma delta epsilon",
                    "char_start": 0,
                    "char_end": 30,
                },
                {
                    "chunk_index": 1,
                    "text": "zeta eta theta iota kappa",
                    "char_start": 31,
                    "char_end": 56,
                },
                {
                    "chunk_index": 2,
                    "text": "lambda mu nu xi omicron pi rho",
                    "char_start": 57,
                    "char_end": 87,
                },
                {
                    "chunk_index": 3,
                    "text": "sigma tau.",
                    "char_start": 88,
                    "char_end": 98,
                },
            ],
        )

    def test_skips_metadata_only_document(self):
        document = {
            "doc_id": "doc_002",
            "metadata_only": 1,
            "body_text": None,
        }

        chunks = chunk_document(document=document, max_chars=32)

        self.assertEqual(chunks, [])

    def test_builds_chunks_table_rows_with_stable_ordering(self):
        document = {
            "doc_id": "doc_003",
            "source_id": "us_bls_news",
            "publisher": "BLS",
            "published_at": "2026-03-10T09:00:00Z",
            "fetched_at": "2026-03-10T09:05:00Z",
            "metadata_only": 0,
            "body_text": "Alpha beta gamma delta epsilon zeta eta theta iota.",
        }

        chunk_rows = build_chunk_rows(document=document, max_chars=24)

        self.assertEqual(
            chunk_rows,
            [
                {
                    "chunk_id": "doc_003_chunk_000",
                    "doc_id": "doc_003",
                    "chunk_index": 0,
                    "text": "Alpha beta gamma delta",
                    "token_count": 4,
                    "char_start": 0,
                    "char_end": 22,
                    "created_at": "2026-03-10T09:05:00Z",
                },
                {
                    "chunk_id": "doc_003_chunk_001",
                    "doc_id": "doc_003",
                    "chunk_index": 1,
                    "text": "epsilon zeta eta theta",
                    "token_count": 4,
                    "char_start": 23,
                    "char_end": 45,
                    "created_at": "2026-03-10T09:05:00Z",
                },
                {
                    "chunk_id": "doc_003_chunk_002",
                    "doc_id": "doc_003",
                    "chunk_index": 2,
                    "text": "iota.",
                    "token_count": 1,
                    "char_start": 46,
                    "char_end": 51,
                    "created_at": "2026-03-10T09:05:00Z",
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
