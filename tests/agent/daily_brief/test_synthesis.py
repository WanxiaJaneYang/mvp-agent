import unittest

from apps.agent.daily_brief.synthesis import build_citation_store, build_synthesis


class DailyBriefSynthesisTests(unittest.TestCase):
    def test_build_synthesis_assigns_core_sections_with_stable_citation_ids(self):
        evidence_items = [
            {
                "chunk_id": "doc_001_chunk_000",
                "doc_id": "doc_001",
                "source_id": "fed_press_releases",
                "publisher": "Federal Reserve",
                "credibility_tier": 1,
                "rank_in_pack": 1,
            },
            {
                "chunk_id": "doc_002_chunk_000",
                "doc_id": "doc_002",
                "source_id": "reuters_business",
                "publisher": "Reuters",
                "credibility_tier": 2,
                "rank_in_pack": 2,
            },
            {
                "chunk_id": "doc_003_chunk_000",
                "doc_id": "doc_003",
                "source_id": "wsj_markets",
                "publisher": "Wall Street Journal",
                "credibility_tier": 2,
                "rank_in_pack": 3,
            },
            {
                "chunk_id": "doc_004_chunk_000",
                "doc_id": "doc_004",
                "source_id": "us_bls_news",
                "publisher": "U.S. Bureau of Labor Statistics",
                "credibility_tier": 1,
                "rank_in_pack": 4,
            },
        ]
        documents_by_id = {
            "doc_001": {
                "canonical_url": "https://example.test/fed",
                "title": "Fed keeps policy steady",
                "published_at": "2026-03-10T14:00:00Z",
                "fetched_at": "2026-03-10T14:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Fed signals steady policy.",
            },
            "doc_002": {
                "canonical_url": "https://example.test/reuters",
                "title": "Markets digest slower growth",
                "published_at": "2026-03-10T15:00:00Z",
                "fetched_at": "2026-03-10T15:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Investors weigh slower growth.",
            },
            "doc_003": {
                "canonical_url": "https://example.test/wsj",
                "title": "Cooling growth draws focus",
                "published_at": "2026-03-10T15:15:00Z",
                "fetched_at": "2026-03-10T15:20:00Z",
                "paywall_policy": "metadata_only",
                "rss_snippet": "Cooling growth becomes the focus.",
            },
            "doc_004": {
                "canonical_url": "https://example.test/bls",
                "title": "Payroll growth moderates",
                "published_at": "2026-03-10T13:30:00Z",
                "fetched_at": "2026-03-10T13:35:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Payroll growth moderates.",
            },
        }
        chunks_by_id = {
            "doc_001_chunk_000": {"text": "Fed keeps policy steady while inflation progress is uneven."},
            "doc_002_chunk_000": {"text": "Investors are weighing slower growth against steady policy."},
            "doc_003_chunk_000": {"text": "Cooling growth is the new market focus."},
            "doc_004_chunk_000": {"text": "Payroll growth moderates and wage gains cool."},
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

        self.assertEqual(sorted(synthesis.keys()), ["counter", "minority", "prevailing", "watch"])
        self.assertEqual(synthesis["prevailing"][0]["citation_ids"], ["cite_001"])
        self.assertEqual(synthesis["counter"][0]["citation_ids"], ["cite_002"])
        self.assertEqual(synthesis["minority"][0]["citation_ids"], ["cite_003"])
        self.assertEqual(synthesis["watch"][0]["citation_ids"], ["cite_004"])

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
