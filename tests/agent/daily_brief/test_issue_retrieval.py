from __future__ import annotations

import unittest

from apps.agent.daily_brief.issue_retrieval import build_brief_corpus_report, build_issue_evidence_scopes


class IssueRetrievalTests(unittest.TestCase):
    def test_build_brief_corpus_report_keeps_diverse_rows(self) -> None:
        report = build_brief_corpus_report(
            fts_rows=[
                {
                    "chunk_id": "chunk_1",
                    "doc_id": "doc_1",
                    "publisher": "Reuters",
                    "source_id": "reuters",
                    "published_at": "2026-03-12T08:00:00Z",
                    "credibility_tier": 2,
                    "text": "Growth cooled while traders watched the next CPI print.",
                },
                {
                    "chunk_id": "chunk_2",
                    "doc_id": "doc_2",
                    "publisher": "Federal Reserve",
                    "source_id": "fed",
                    "published_at": "2026-03-12T07:00:00Z",
                    "credibility_tier": 1,
                    "text": "Officials kept policy language cautious.",
                },
                {
                    "chunk_id": "chunk_3",
                    "doc_id": "doc_3",
                    "publisher": "Wall Street Journal",
                    "source_id": "wsj",
                    "published_at": "2026-03-12T06:00:00Z",
                    "credibility_tier": 2,
                    "text": "Markets widened the policy gap interpretation.",
                },
            ],
            pack_size=3,
        )

        self.assertEqual(len(report["items"]), 3)
        self.assertEqual(report["diversity_stats"]["unique_publishers"], 3)

    def test_build_issue_evidence_scopes_generates_per_issue_coverage(self) -> None:
        scopes = build_issue_evidence_scopes(
            brief_plan={
                "brief_id": "brief_2026-03-12_run_demo",
                "brief_thesis": "Growth and policy are the main debates.",
                "top_takeaways": [],
                "issue_budget": 2,
                "render_mode": "full",
                "source_scarcity_mode": "normal",
                "candidate_issue_seeds": ["growth cooling", "policy caution"],
                "issue_order": ["seed_001", "seed_002"],
                "watchlist": [],
                "reason_codes": ["two_distinct_debates_supported"],
            },
            corpus_items=[
                {
                    "chunk_id": "chunk_1",
                    "doc_id": "doc_1",
                    "source_id": "reuters",
                    "publisher": "Reuters",
                    "credibility_tier": 2,
                    "retrieval_score": 0.91,
                    "semantic_score": 0.80,
                    "recency_score": 0.90,
                    "credibility_score": 0.80,
                    "rank_in_pack": 1,
                },
                {
                    "chunk_id": "chunk_2",
                    "doc_id": "doc_2",
                    "source_id": "fed",
                    "publisher": "Federal Reserve",
                    "credibility_tier": 1,
                    "retrieval_score": 0.88,
                    "semantic_score": 0.70,
                    "recency_score": 0.90,
                    "credibility_score": 1.00,
                    "rank_in_pack": 2,
                },
            ],
            fts_rows=[
                {
                    "chunk_id": "chunk_1",
                    "doc_id": "doc_1",
                    "publisher": "Reuters",
                    "source_id": "reuters",
                    "published_at": "2026-03-12T08:00:00Z",
                    "text": "Growth cooling challenged the soft-landing view.",
                },
                {
                    "chunk_id": "chunk_2",
                    "doc_id": "doc_2",
                    "publisher": "Federal Reserve",
                    "source_id": "fed",
                    "published_at": "2026-03-12T07:00:00Z",
                    "text": "Policy caution remained the official line ahead of CPI.",
                },
            ],
            registry={
                "reuters": {"tags": ["market_narrative"]},
                "fed": {"tags": ["policy_centralbank"]},
            },
        )

        self.assertEqual(len(scopes), 2)
        self.assertEqual(scopes[0]["issue_id"], "issue_001")
        self.assertIn("coverage_summary", scopes[0])

    def test_build_issue_evidence_scopes_keeps_fallback_primary_chunks_distinct(self) -> None:
        scopes = build_issue_evidence_scopes(
            brief_plan={
                "brief_id": "brief_2026-03-12_run_demo",
                "brief_thesis": "Growth is the only real seed, but scopes should still stay distinct.",
                "top_takeaways": [],
                "issue_budget": 2,
                "render_mode": "full",
                "source_scarcity_mode": "normal",
                "candidate_issue_seeds": ["growth", "growth"],
                "issue_order": ["seed_001", "seed_002"],
                "watchlist": [],
                "reason_codes": ["two_distinct_debates_supported"],
            },
            corpus_items=[
                {
                    "chunk_id": "chunk_1",
                    "doc_id": "doc_1",
                    "source_id": "reuters",
                    "publisher": "Reuters",
                    "credibility_tier": 2,
                    "retrieval_score": 0.95,
                    "semantic_score": 0.90,
                    "recency_score": 0.90,
                    "credibility_score": 0.80,
                    "rank_in_pack": 1,
                },
                {
                    "chunk_id": "chunk_2",
                    "doc_id": "doc_2",
                    "source_id": "fed",
                    "publisher": "Federal Reserve",
                    "credibility_tier": 1,
                    "retrieval_score": 0.85,
                    "semantic_score": 0.70,
                    "recency_score": 0.88,
                    "credibility_score": 1.00,
                    "rank_in_pack": 2,
                },
            ],
            fts_rows=[
                {
                    "chunk_id": "chunk_1",
                    "doc_id": "doc_1",
                    "publisher": "Reuters",
                    "source_id": "reuters",
                    "published_at": "2026-03-12T08:00:00Z",
                    "text": "Growth cooling challenged the soft-landing view.",
                },
                {
                    "chunk_id": "chunk_2",
                    "doc_id": "doc_2",
                    "publisher": "Federal Reserve",
                    "source_id": "fed",
                    "published_at": "2026-03-12T07:00:00Z",
                    "text": "Growth remained the official focus.",
                },
            ],
            registry={
                "reuters": {"tags": ["market_narrative"]},
                "fed": {"tags": ["policy_centralbank"]},
            },
        )

        self.assertEqual(scopes[0]["primary_chunk_ids"], ["chunk_1", "chunk_2"])
        self.assertEqual(scopes[1]["primary_chunk_ids"], [])

    def test_build_issue_evidence_scopes_keeps_bucket_assignments_semantically_distinct(self) -> None:
        scopes = build_issue_evidence_scopes(
            brief_plan={
                "brief_id": "brief_2026-03-12_run_demo",
                "brief_thesis": "Growth cooling is the main debate.",
                "top_takeaways": [],
                "issue_budget": 1,
                "render_mode": "full",
                "source_scarcity_mode": "normal",
                "candidate_issue_seeds": ["growth cooling"],
                "issue_order": ["seed_001"],
                "watchlist": [],
                "reason_codes": ["single_distinct_debate_supported"],
            },
            corpus_items=[
                {
                    "chunk_id": "chunk_1",
                    "doc_id": "doc_1",
                    "source_id": "reuters",
                    "publisher": "Reuters",
                    "credibility_tier": 2,
                    "retrieval_score": 0.95,
                    "semantic_score": 0.95,
                    "recency_score": 0.90,
                    "credibility_score": 0.80,
                    "rank_in_pack": 1,
                },
                {
                    "chunk_id": "chunk_2",
                    "doc_id": "doc_2",
                    "source_id": "fed",
                    "publisher": "Federal Reserve",
                    "credibility_tier": 1,
                    "retrieval_score": 0.92,
                    "semantic_score": 0.92,
                    "recency_score": 0.88,
                    "credibility_score": 1.00,
                    "rank_in_pack": 2,
                },
                {
                    "chunk_id": "chunk_3",
                    "doc_id": "doc_3",
                    "source_id": "wsj",
                    "publisher": "Wall Street Journal",
                    "credibility_tier": 2,
                    "retrieval_score": 0.89,
                    "semantic_score": 0.89,
                    "recency_score": 0.86,
                    "credibility_score": 0.80,
                    "rank_in_pack": 3,
                },
                {
                    "chunk_id": "chunk_4",
                    "doc_id": "doc_4",
                    "source_id": "ft",
                    "publisher": "Financial Times",
                    "credibility_tier": 2,
                    "retrieval_score": 0.83,
                    "semantic_score": 0.83,
                    "recency_score": 0.82,
                    "credibility_score": 0.80,
                    "rank_in_pack": 4,
                },
                {
                    "chunk_id": "chunk_5",
                    "doc_id": "doc_5",
                    "source_id": "bloomberg",
                    "publisher": "Bloomberg",
                    "credibility_tier": 2,
                    "retrieval_score": 0.79,
                    "semantic_score": 0.79,
                    "recency_score": 0.80,
                    "credibility_score": 0.80,
                    "rank_in_pack": 5,
                },
                {
                    "chunk_id": "chunk_6",
                    "doc_id": "doc_6",
                    "source_id": "ap",
                    "publisher": "Associated Press",
                    "credibility_tier": 2,
                    "retrieval_score": 0.76,
                    "semantic_score": 0.76,
                    "recency_score": 0.78,
                    "credibility_score": 0.80,
                    "rank_in_pack": 6,
                },
            ],
            fts_rows=[
                {
                    "chunk_id": "chunk_1",
                    "doc_id": "doc_1",
                    "publisher": "Reuters",
                    "source_id": "reuters",
                    "published_at": "2026-03-12T08:00:00Z",
                    "text": "Growth cooling remained the dominant macro debate after weaker data.",
                },
                {
                    "chunk_id": "chunk_2",
                    "doc_id": "doc_2",
                    "publisher": "Federal Reserve",
                    "source_id": "fed",
                    "published_at": "2026-03-12T07:00:00Z",
                    "text": "Growth cooling spread across manufacturing and services.",
                },
                {
                    "chunk_id": "chunk_3",
                    "doc_id": "doc_3",
                    "publisher": "Wall Street Journal",
                    "source_id": "wsj",
                    "published_at": "2026-03-12T06:00:00Z",
                    "text": "Growth cooling kept the baseline soft-landing view fragile.",
                },
                {
                    "chunk_id": "chunk_4",
                    "doc_id": "doc_4",
                    "publisher": "Financial Times",
                    "source_id": "ft",
                    "published_at": "2026-03-12T05:00:00Z",
                    "text": "Analysts challenge the growth cooling consensus ahead of payrolls.",
                },
                {
                    "chunk_id": "chunk_5",
                    "doc_id": "doc_5",
                    "publisher": "Bloomberg",
                    "source_id": "bloomberg",
                    "published_at": "2026-03-12T04:00:00Z",
                    "text": "A contrarian minority says growth cooling will reverse quickly.",
                },
                {
                    "chunk_id": "chunk_6",
                    "doc_id": "doc_6",
                    "publisher": "Associated Press",
                    "source_id": "ap",
                    "published_at": "2026-03-12T03:00:00Z",
                    "text": "Growth cooling watch now turns to next payrolls risk.",
                },
            ],
            registry={
                "reuters": {"tags": ["market_narrative"]},
                "fed": {"tags": ["policy_centralbank"]},
                "wsj": {"tags": ["market_commentary"]},
                "ft": {"tags": ["market_commentary"]},
                "bloomberg": {"tags": ["market_commentary"]},
                "ap": {"tags": ["market_commentary"]},
            },
        )

        scope = scopes[0]
        self.assertEqual(scope["opposing_chunk_ids"], ["chunk_4"])
        self.assertEqual(scope["minority_chunk_ids"], ["chunk_5"])
        self.assertEqual(scope["watch_chunk_ids"], ["chunk_6"])
        self.assertEqual(
            len(
                set(
                    scope["primary_chunk_ids"]
                    + scope["opposing_chunk_ids"]
                    + scope["minority_chunk_ids"]
                    + scope["watch_chunk_ids"]
                )
            ),
            len(
                scope["primary_chunk_ids"]
                + scope["opposing_chunk_ids"]
                + scope["minority_chunk_ids"]
                + scope["watch_chunk_ids"]
            ),
        )

    def test_build_issue_evidence_scopes_blocks_cross_issue_bucket_reuse(self) -> None:
        scopes = build_issue_evidence_scopes(
            brief_plan={
                "brief_id": "brief_2026-03-12_run_demo",
                "brief_thesis": "Growth cooling is overrepresented and duplicate issue seeds should not borrow evidence.",
                "top_takeaways": [],
                "issue_budget": 2,
                "render_mode": "full",
                "source_scarcity_mode": "normal",
                "candidate_issue_seeds": ["growth cooling", "growth cooling"],
                "issue_order": ["seed_001", "seed_002"],
                "watchlist": [],
                "reason_codes": ["duplicate_issue_seeds_present"],
            },
            corpus_items=[
                {
                    "chunk_id": "chunk_1",
                    "doc_id": "doc_1",
                    "source_id": "reuters",
                    "publisher": "Reuters",
                    "credibility_tier": 2,
                    "retrieval_score": 0.95,
                    "semantic_score": 0.95,
                    "recency_score": 0.90,
                    "credibility_score": 0.80,
                    "rank_in_pack": 1,
                },
                {
                    "chunk_id": "chunk_2",
                    "doc_id": "doc_2",
                    "source_id": "fed",
                    "publisher": "Federal Reserve",
                    "credibility_tier": 1,
                    "retrieval_score": 0.92,
                    "semantic_score": 0.92,
                    "recency_score": 0.88,
                    "credibility_score": 1.00,
                    "rank_in_pack": 2,
                },
                {
                    "chunk_id": "chunk_3",
                    "doc_id": "doc_3",
                    "source_id": "wsj",
                    "publisher": "Wall Street Journal",
                    "credibility_tier": 2,
                    "retrieval_score": 0.89,
                    "semantic_score": 0.89,
                    "recency_score": 0.86,
                    "credibility_score": 0.80,
                    "rank_in_pack": 3,
                },
                {
                    "chunk_id": "chunk_4",
                    "doc_id": "doc_4",
                    "source_id": "ft",
                    "publisher": "Financial Times",
                    "credibility_tier": 2,
                    "retrieval_score": 0.83,
                    "semantic_score": 0.83,
                    "recency_score": 0.82,
                    "credibility_score": 0.80,
                    "rank_in_pack": 4,
                },
            ],
            fts_rows=[
                {
                    "chunk_id": "chunk_1",
                    "doc_id": "doc_1",
                    "publisher": "Reuters",
                    "source_id": "reuters",
                    "published_at": "2026-03-12T08:00:00Z",
                    "text": "Growth cooling remained the dominant macro debate after weaker data.",
                },
                {
                    "chunk_id": "chunk_2",
                    "doc_id": "doc_2",
                    "publisher": "Federal Reserve",
                    "source_id": "fed",
                    "published_at": "2026-03-12T07:00:00Z",
                    "text": "Growth cooling spread across manufacturing and services.",
                },
                {
                    "chunk_id": "chunk_3",
                    "doc_id": "doc_3",
                    "publisher": "Wall Street Journal",
                    "source_id": "wsj",
                    "published_at": "2026-03-12T06:00:00Z",
                    "text": "Growth cooling kept the baseline soft-landing view fragile.",
                },
                {
                    "chunk_id": "chunk_4",
                    "doc_id": "doc_4",
                    "publisher": "Financial Times",
                    "source_id": "ft",
                    "published_at": "2026-03-12T05:00:00Z",
                    "text": "Analysts challenge the growth cooling consensus.",
                },
            ],
            registry={
                "reuters": {"tags": ["market_narrative"]},
                "fed": {"tags": ["policy_centralbank"]},
                "wsj": {"tags": ["market_commentary"]},
                "ft": {"tags": ["market_commentary"]},
            },
        )

        first_issue_ids = set(
            scopes[0]["primary_chunk_ids"]
            + scopes[0]["opposing_chunk_ids"]
            + scopes[0]["minority_chunk_ids"]
            + scopes[0]["watch_chunk_ids"]
        )
        second_issue_ids = set(
            scopes[1]["primary_chunk_ids"]
            + scopes[1]["opposing_chunk_ids"]
            + scopes[1]["minority_chunk_ids"]
            + scopes[1]["watch_chunk_ids"]
        )

        self.assertFalse(first_issue_ids & second_issue_ids)

    def test_build_brief_corpus_report_treats_invalid_published_at_as_missing(self) -> None:
        report = build_brief_corpus_report(
            fts_rows=[
                {
                    "chunk_id": "chunk_1",
                    "doc_id": "doc_1",
                    "publisher": "Reuters",
                    "source_id": "reuters",
                    "published_at": "not-a-timestamp",
                    "credibility_tier": 1,
                    "text": "Growth cooled while traders watched the next CPI print.",
                },
                {
                    "chunk_id": "chunk_2",
                    "doc_id": "doc_2",
                    "publisher": "Federal Reserve",
                    "source_id": "fed",
                    "published_at": "2026-03-12T07:00:00Z",
                    "credibility_tier": 1,
                    "text": "Officials kept policy language cautious.",
                },
            ],
            pack_size=2,
        )

        self.assertEqual([item["chunk_id"] for item in report["items"]], ["chunk_2", "chunk_1"])


if __name__ == "__main__":
    unittest.main()
