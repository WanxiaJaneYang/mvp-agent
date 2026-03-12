import unittest

from apps.agent.retrieval.evidence_pack import build_evidence_pack, build_evidence_pack_report


class EvidencePackTests(unittest.TestCase):
    def test_report_enforces_publisher_cap_when_alternatives_exist(self):
        fts_rows = [
            {
                "chunk_id": "chunk_001",
                "doc_id": "doc_001",
                "text": "inflation inflation inflation",
                "source_id": "src_reuters_a",
                "publisher": "Reuters",
                "published_at": "2026-03-10T10:00:00Z",
                "credibility_tier": 2,
            },
            {
                "chunk_id": "chunk_002",
                "doc_id": "doc_002",
                "text": "inflation inflation rates",
                "source_id": "src_reuters_b",
                "publisher": "Reuters",
                "published_at": "2026-03-10T09:00:00Z",
                "credibility_tier": 2,
            },
            {
                "chunk_id": "chunk_003",
                "doc_id": "doc_003",
                "text": "inflation rates cooling",
                "source_id": "src_reuters_c",
                "publisher": "Reuters",
                "published_at": "2026-03-10T08:00:00Z",
                "credibility_tier": 2,
            },
            {
                "chunk_id": "chunk_004",
                "doc_id": "doc_004",
                "text": "inflation update from fed",
                "source_id": "src_fed",
                "publisher": "Federal Reserve",
                "published_at": "2026-03-10T07:00:00Z",
                "credibility_tier": 1,
            },
            {
                "chunk_id": "chunk_005",
                "doc_id": "doc_005",
                "text": "inflation update from bls",
                "source_id": "src_bls",
                "publisher": "BLS",
                "published_at": "2026-03-10T06:00:00Z",
                "credibility_tier": 1,
            },
            {
                "chunk_id": "chunk_006",
                "doc_id": "doc_006",
                "text": "inflation update from ecb",
                "source_id": "src_ecb",
                "publisher": "ECB",
                "published_at": "2026-03-10T05:00:00Z",
                "credibility_tier": 1,
            },
        ]

        report = build_evidence_pack_report(fts_rows=fts_rows, query_text="inflation", pack_size=5)

        self.assertEqual(report["diversity_check"], "pass")
        self.assertEqual(report["diversity_stats"]["max_publisher_pct"], 40.0)
        self.assertEqual(sum(1 for item in report["items"] if item["publisher"] == "Reuters"), 2)

    def test_report_flags_fail_when_candidate_pool_cannot_meet_diversity_rules(self):
        fts_rows = [
            {
                "chunk_id": "chunk_001",
                "doc_id": "doc_001",
                "text": "inflation inflation inflation",
                "source_id": "src_only_a",
                "publisher": "Single Publisher",
                "published_at": "2026-03-10T10:00:00Z",
                "credibility_tier": 2,
            },
            {
                "chunk_id": "chunk_002",
                "doc_id": "doc_002",
                "text": "inflation rates stay high",
                "source_id": "src_only_b",
                "publisher": "Single Publisher",
                "published_at": "2026-03-10T09:00:00Z",
                "credibility_tier": 2,
            },
        ]

        report = build_evidence_pack_report(fts_rows=fts_rows, query_text="inflation", pack_size=2)

        self.assertEqual(report["diversity_check"], "fail")
        self.assertGreater(report["diversity_stats"]["max_publisher_pct"], 40.0)
        self.assertTrue(any("publisher dominance" in note.lower() for note in report["notes"]))

    def test_orders_results_by_retrieval_score(self):
        fts_rows = [
            {
                "chunk_id": "chunk_002",
                "doc_id": "doc_002",
                "text": "inflation slows but rates stay restrictive",
                "source_id": "src_reuters",
                "publisher": "Reuters",
                "published_at": "2026-03-08T10:00:00Z",
                "credibility_tier": 2,
            },
            {
                "chunk_id": "chunk_001",
                "doc_id": "doc_001",
                "text": "inflation inflation inflation and rates",
                "source_id": "src_fed",
                "publisher": "Federal Reserve",
                "published_at": "2026-03-10T10:00:00Z",
                "credibility_tier": 1,
            },
            {
                "chunk_id": "chunk_003",
                "doc_id": "doc_003",
                "text": "employment gains accelerate",
                "source_id": "src_blog",
                "publisher": "Macro Blog",
                "published_at": "2026-03-10T08:00:00Z",
                "credibility_tier": 3,
            },
        ]

        pack = build_evidence_pack(fts_rows=fts_rows, query_text="inflation rates", pack_size=3)

        self.assertEqual([row["chunk_id"] for row in pack], ["chunk_001", "chunk_002"])
        self.assertEqual(pack[0]["rank_in_pack"], 1)
        self.assertEqual(pack[1]["rank_in_pack"], 2)
        self.assertGreater(pack[0]["retrieval_score"], pack[1]["retrieval_score"])

    def test_caps_pack_size_after_sorting(self):
        fts_rows = [
            {
                "chunk_id": "chunk_003",
                "doc_id": "doc_003",
                "text": "inflation",
                "source_id": "src_c",
                "publisher": "C",
                "published_at": "2026-03-08T10:00:00Z",
                "credibility_tier": 2,
            },
            {
                "chunk_id": "chunk_001",
                "doc_id": "doc_001",
                "text": "inflation inflation",
                "source_id": "src_a",
                "publisher": "A",
                "published_at": "2026-03-10T10:00:00Z",
                "credibility_tier": 1,
            },
            {
                "chunk_id": "chunk_002",
                "doc_id": "doc_002",
                "text": "inflation rates",
                "source_id": "src_b",
                "publisher": "B",
                "published_at": "2026-03-09T10:00:00Z",
                "credibility_tier": 2,
            },
        ]

        pack = build_evidence_pack(fts_rows=fts_rows, query_text="inflation", pack_size=2)

        self.assertEqual(len(pack), 2)
        self.assertEqual([row["chunk_id"] for row in pack], ["chunk_001", "chunk_002"])

    def test_tie_breaks_by_newer_timestamp_then_chunk_id(self):
        fts_rows = [
            {
                "chunk_id": "chunk_002",
                "doc_id": "doc_002",
                "text": "inflation",
                "source_id": "src_b",
                "publisher": "B",
                "published_at": "2026-03-09T10:00:00Z",
                "credibility_tier": 2,
            },
            {
                "chunk_id": "chunk_001",
                "doc_id": "doc_001",
                "text": "inflation",
                "source_id": "src_a",
                "publisher": "A",
                "published_at": "2026-03-09T10:00:00Z",
                "credibility_tier": 2,
            },
            {
                "chunk_id": "chunk_003",
                "doc_id": "doc_003",
                "text": "inflation",
                "source_id": "src_c",
                "publisher": "C",
                "published_at": "2026-03-10T10:00:00Z",
                "credibility_tier": 2,
            },
        ]

        pack = build_evidence_pack(fts_rows=fts_rows, query_text="inflation", pack_size=3)

        self.assertEqual([row["chunk_id"] for row in pack], ["chunk_003", "chunk_001", "chunk_002"])

    def test_emits_evidence_pack_item_compatible_rows(self):
        fts_rows = [
            {
                "chunk_id": "chunk_001",
                "doc_id": "doc_001",
                "text": "inflation inflation",
                "source_id": "src_a",
                "publisher": "Federal Reserve",
                "published_at": "2026-03-10T10:00:00Z",
                "credibility_tier": 1,
            }
        ]

        pack = build_evidence_pack(fts_rows=fts_rows, query_text="inflation", pack_size=1)

        self.assertEqual(
            pack,
            [
                {
                    "chunk_id": "chunk_001",
                    "source_id": "src_a",
                    "publisher": "Federal Reserve",
                    "credibility_tier": 1,
                    "retrieval_score": pack[0]["retrieval_score"],
                    "semantic_score": pack[0]["semantic_score"],
                    "recency_score": 1.0,
                    "credibility_score": 1.0,
                    "rank_in_pack": 1,
                }
            ],
        )
        self.assertGreater(pack[0]["retrieval_score"], 0.0)
        self.assertGreater(pack[0]["semantic_score"], 0.0)

    def test_missing_required_row_field_raises_value_error(self):
        fts_rows = [
            {
                "chunk_id": "chunk_001",
                "doc_id": "doc_001",
                "text": "inflation",
                "source_id": "src_a",
                "published_at": "2026-03-10T10:00:00Z",
                "credibility_tier": 1,
            }
        ]

        with self.assertRaises(ValueError):
            build_evidence_pack(fts_rows=fts_rows, query_text="inflation", pack_size=1)

    def test_invalid_credibility_tier_raises_value_error(self):
        fts_rows = [
            {
                "chunk_id": "chunk_001",
                "doc_id": "doc_001",
                "text": "inflation",
                "source_id": "src_a",
                "publisher": "Federal Reserve",
                "published_at": "2026-03-10T10:00:00Z",
                "credibility_tier": 9,
            }
        ]

        with self.assertRaises(ValueError):
            build_evidence_pack(fts_rows=fts_rows, query_text="inflation", pack_size=1)

    def test_recency_normalization_only_uses_matching_rows(self):
        fts_rows = [
            {
                "chunk_id": "chunk_001",
                "doc_id": "doc_001",
                "text": "inflation inflation",
                "source_id": "src_a",
                "publisher": "Federal Reserve",
                "published_at": "2026-03-09T10:00:00Z",
                "credibility_tier": 1,
            },
            {
                "chunk_id": "chunk_002",
                "doc_id": "doc_002",
                "text": "inflation rates",
                "source_id": "src_b",
                "publisher": "Reuters",
                "published_at": "2026-03-10T10:00:00Z",
                "credibility_tier": 2,
            },
            {
                "chunk_id": "chunk_099",
                "doc_id": "doc_099",
                "text": "employment gains accelerate",
                "source_id": "src_c",
                "publisher": "Macro Blog",
                "published_at": "2026-03-20T10:00:00Z",
                "credibility_tier": 3,
            },
        ]

        pack = build_evidence_pack(fts_rows=fts_rows, query_text="inflation", pack_size=2)

        self.assertEqual(pack[0]["chunk_id"], "chunk_001")
        self.assertEqual(pack[1]["chunk_id"], "chunk_002")
        self.assertEqual(pack[0]["recency_score"], 0.0)
        self.assertEqual(pack[1]["recency_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
