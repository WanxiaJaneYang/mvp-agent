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


if __name__ == "__main__":
    unittest.main()
