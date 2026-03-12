import unittest

from apps.agent.daily_brief.synthesis import build_citation_store, build_synthesis


class DailyBriefSynthesisTests(unittest.TestCase):
    def test_build_synthesis_groups_issue_arguments_under_one_issue(self):
        evidence_items = [
            {
                "chunk_id": "doc_001_chunk_000",
                "doc_id": "doc_001",
                "source_id": "reuters_business",
                "publisher": "Reuters",
                "credibility_tier": 2,
                "rank_in_pack": 1,
            },
            {
                "chunk_id": "doc_002_chunk_000",
                "doc_id": "doc_002",
                "source_id": "wsj_markets",
                "publisher": "Wall Street Journal",
                "credibility_tier": 2,
                "rank_in_pack": 2,
            },
            {
                "chunk_id": "doc_003_chunk_000",
                "doc_id": "doc_003",
                "source_id": "fed_press_releases",
                "publisher": "Federal Reserve",
                "credibility_tier": 1,
                "rank_in_pack": 3,
            },
            {
                "chunk_id": "doc_004_chunk_000",
                "doc_id": "doc_004",
                "source_id": "us_bea_news",
                "publisher": "U.S. Bureau of Economic Analysis",
                "credibility_tier": 1,
                "rank_in_pack": 4,
            },
        ]
        documents_by_id = {
            "doc_001": {
                "canonical_url": "https://example.test/oil-prevailing",
                "title": "Oil prices extend rally on supply risks",
                "published_at": "2026-03-10T14:00:00Z",
                "fetched_at": "2026-03-10T14:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Supply disruptions keep oil traders bullish.",
            },
            "doc_002": {
                "canonical_url": "https://example.test/oil-counter",
                "title": "Some traders expect oil prices to stabilize soon",
                "published_at": "2026-03-10T15:00:00Z",
                "fetched_at": "2026-03-10T15:05:00Z",
                "paywall_policy": "metadata_only",
                "rss_snippet": "Demand concerns may cap the rally.",
            },
            "doc_003": {
                "canonical_url": "https://example.test/oil-minority",
                "title": "Long-term crude upside remains but the short-term path is less drastic",
                "published_at": "2026-03-10T15:15:00Z",
                "fetched_at": "2026-03-10T15:20:00Z",
                "paywall_policy": "full",
                "rss_snippet": "A smaller camp sees gradual upside, not a sharp spike.",
            },
            "doc_004": {
                "canonical_url": "https://example.test/oil-watch",
                "title": "OPEC guidance will shape the next oil move",
                "published_at": "2026-03-10T13:30:00Z",
                "fetched_at": "2026-03-10T13:35:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Next week's supply guidance could challenge the current view.",
            },
        }
        chunks_by_id = {
            "doc_001_chunk_000": {"text": "Oil prices extended their rally as supply disruptions stayed in focus."},
            "doc_002_chunk_000": {"text": "Some traders expect oil prices to stabilize as demand expectations soften."},
            "doc_003_chunk_000": {"text": "A minority view sees longer-term upside with a milder short-term move."},
            "doc_004_chunk_000": {"text": "Upcoming OPEC guidance is the key catalyst to watch next."},
        }

        citations = build_citation_store(
            evidence_items=evidence_items,
            documents_by_id=documents_by_id,
            chunks_by_id=chunks_by_id,
        )
        synthesis = build_synthesis(
            evidence_items=evidence_items,
            documents_by_id=documents_by_id,
            citation_store=citations,
        )

        self.assertEqual(list(synthesis.keys()), ["issues"])
        self.assertEqual(len(synthesis["issues"]), 1)

        oil_issue = synthesis["issues"][0]
        self.assertEqual(oil_issue["issue_id"], "issue_001")
        self.assertIn("oil", oil_issue["title"].lower())
        self.assertTrue(oil_issue["summary"])
        self.assertEqual(oil_issue["prevailing"][0]["citation_ids"], ["cite_001"])
        self.assertEqual(oil_issue["counter"][0]["citation_ids"], ["cite_002"])
        self.assertEqual(oil_issue["minority"][0]["citation_ids"], ["cite_003"])
        self.assertEqual(oil_issue["watch"][0]["citation_ids"], ["cite_004"])
        self.assertEqual(
            oil_issue["prevailing"][0]["evidence"][0]["support_text"],
            "Oil prices extended their rally as supply disruptions stayed in focus.",
        )
        self.assertEqual(
            oil_issue["counter"][0]["evidence"][0]["support_text"],
            "Demand concerns may cap the rally.",
        )

    def test_build_synthesis_splits_unrelated_documents_into_multiple_issues(self):
        evidence_items = [
            {
                "chunk_id": "doc_001_chunk_000",
                "doc_id": "doc_001",
                "source_id": "reuters_business",
                "publisher": "Reuters",
                "credibility_tier": 2,
                "rank_in_pack": 1,
            },
            {
                "chunk_id": "doc_002_chunk_000",
                "doc_id": "doc_002",
                "source_id": "fed_press_releases",
                "publisher": "Federal Reserve",
                "credibility_tier": 1,
                "rank_in_pack": 2,
            },
            {
                "chunk_id": "doc_003_chunk_000",
                "doc_id": "doc_003",
                "source_id": "us_bls_news",
                "publisher": "U.S. Bureau of Labor Statistics",
                "credibility_tier": 1,
                "rank_in_pack": 3,
            },
            {
                "chunk_id": "doc_004_chunk_000",
                "doc_id": "doc_004",
                "source_id": "us_bea_news",
                "publisher": "U.S. Bureau of Economic Analysis",
                "credibility_tier": 1,
                "rank_in_pack": 4,
            },
        ]
        documents_by_id = {
            "doc_001": {
                "canonical_url": "https://example.test/oil-prevailing",
                "title": "Oil prices extend rally on supply risks",
                "published_at": "2026-03-10T14:00:00Z",
                "fetched_at": "2026-03-10T14:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Supply disruptions keep oil traders bullish.",
            },
            "doc_002": {
                "canonical_url": "https://example.test/oil-counter",
                "title": "Fed says policy is steady despite crude volatility",
                "published_at": "2026-03-10T15:00:00Z",
                "fetched_at": "2026-03-10T15:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Officials see no immediate policy response to oil moves.",
            },
            "doc_003": {
                "canonical_url": "https://example.test/jobs-prevailing",
                "title": "Payroll growth moderates in the latest report",
                "published_at": "2026-03-10T15:15:00Z",
                "fetched_at": "2026-03-10T15:20:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Labor-market cooling is becoming more visible.",
            },
            "doc_004": {
                "canonical_url": "https://example.test/jobs-watch",
                "title": "Consumer spending growth softens after job gains cool",
                "published_at": "2026-03-10T13:30:00Z",
                "fetched_at": "2026-03-10T13:35:00Z",
                "paywall_policy": "full",
                "rss_snippet": "The next spending release will test the growth slowdown thesis.",
            },
        }
        chunks_by_id = {
            "doc_001_chunk_000": {"text": "Oil prices extended their rally as supply disruptions stayed in focus."},
            "doc_002_chunk_000": {"text": "Policy officials are not treating oil moves as enough to change the current stance."},
            "doc_003_chunk_000": {"text": "Payroll growth moderated and wage gains cooled in the latest release."},
            "doc_004_chunk_000": {"text": "Consumer spending growth softened after labor-market cooling became more visible."},
        }

        citations = build_citation_store(
            evidence_items=evidence_items,
            documents_by_id=documents_by_id,
            chunks_by_id=chunks_by_id,
        )
        synthesis = build_synthesis(
            evidence_items=evidence_items,
            documents_by_id=documents_by_id,
            citation_store=citations,
        )

        self.assertEqual(len(synthesis["issues"]), 2)
        issue_titles = [issue["title"].lower() for issue in synthesis["issues"]]
        self.assertTrue(any("oil" in title for title in issue_titles))
        self.assertTrue(any("growth" in title or "payroll" in title for title in issue_titles))

    def test_build_citation_store_omits_quote_text_for_metadata_only_sources(self):
        citations = build_citation_store(
            evidence_items=[
                {
                    "chunk_id": "doc_003_chunk_000",
                    "doc_id": "doc_003",
                    "source_id": "wsj_markets",
                    "publisher": "Wall Street Journal",
                    "credibility_tier": 2,
                    "rank_in_pack": 1,
                }
            ],
            documents_by_id={
                "doc_003": {
                    "canonical_url": "https://example.test/wsj",
                    "title": "Cooling growth draws focus",
                    "published_at": "2026-03-10T15:15:00Z",
                    "fetched_at": "2026-03-10T15:20:00Z",
                    "paywall_policy": "metadata_only",
                    "rss_snippet": "Cooling growth becomes the focus.",
                }
            },
            chunks_by_id={"doc_003_chunk_000": {"text": "Cooling growth is the new market focus."}},
        )

        self.assertIsNone(citations["cite_001"].get("quote_text"))
        self.assertEqual(citations["cite_001"]["snippet_text"], "Cooling growth becomes the focus.")


if __name__ == "__main__":
    unittest.main()
