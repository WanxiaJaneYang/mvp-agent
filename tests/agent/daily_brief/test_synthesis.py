import unittest

from apps.agent.daily_brief.synthesis import build_citation_store, build_synthesis


class DailyBriefSynthesisTests(unittest.TestCase):
    def test_build_synthesis_assigns_sections_from_evidence_signals_not_rank(self):
        evidence_items = [
            {
                "chunk_id": "doc_watch_chunk_000",
                "doc_id": "doc_watch",
                "source_id": "bls_preview",
                "publisher": "BLS Preview Desk",
                "credibility_tier": 1,
                "rank_in_pack": 1,
            },
            {
                "chunk_id": "doc_minority_chunk_000",
                "doc_id": "doc_minority",
                "source_id": "market_commentary",
                "publisher": "Market Commentary",
                "credibility_tier": 3,
                "rank_in_pack": 2,
            },
            {
                "chunk_id": "doc_prevailing_chunk_000",
                "doc_id": "doc_prevailing",
                "source_id": "fed_press_releases",
                "publisher": "Federal Reserve",
                "credibility_tier": 1,
                "rank_in_pack": 3,
            },
            {
                "chunk_id": "doc_counter_chunk_000",
                "doc_id": "doc_counter",
                "source_id": "reuters_business",
                "publisher": "Reuters",
                "credibility_tier": 2,
                "rank_in_pack": 4,
            },
        ]
        documents_by_id = {
            "doc_watch": {
                "canonical_url": "https://example.test/watch",
                "title": "Watch Friday CPI for shelter inflation",
                "published_at": "2026-03-10T16:00:00Z",
                "fetched_at": "2026-03-10T16:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Markets are watching Friday CPI for shelter inflation surprises.",
            },
            "doc_minority": {
                "canonical_url": "https://example.test/minority",
                "title": "Minority view warns inflation could reaccelerate",
                "published_at": "2026-03-10T15:30:00Z",
                "fetched_at": "2026-03-10T15:35:00Z",
                "paywall_policy": "full",
                "rss_snippet": "A minority of investors still expects inflation to reaccelerate.",
            },
            "doc_prevailing": {
                "canonical_url": "https://example.test/prevailing",
                "title": "Fed keeps policy steady",
                "published_at": "2026-03-10T14:00:00Z",
                "fetched_at": "2026-03-10T14:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Fed officials kept policy steady while inflation progress remained uneven.",
            },
            "doc_counter": {
                "canonical_url": "https://example.test/counter",
                "title": "Bond traders push back on soft-landing consensus",
                "published_at": "2026-03-10T14:30:00Z",
                "fetched_at": "2026-03-10T14:35:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Bond traders push back on the soft-landing consensus as growth cools.",
            },
        }
        chunks_by_id = {
            "doc_watch_chunk_000": {"text": "Watch Friday CPI for shelter inflation surprises."},
            "doc_minority_chunk_000": {"text": "A minority of investors still expects inflation to reaccelerate."},
            "doc_prevailing_chunk_000": {"text": "Fed officials kept policy steady while inflation progress remained uneven."},
            "doc_counter_chunk_000": {"text": "Bond traders push back on the soft-landing consensus as growth cools."},
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
        self.assertEqual(synthesis["prevailing"][0]["citation_ids"], ["cite_003"])
        self.assertEqual(synthesis["counter"][0]["citation_ids"], ["cite_004"])
        self.assertEqual(synthesis["minority"][0]["citation_ids"], ["cite_002"])
        self.assertEqual(synthesis["watch"][0]["citation_ids"], ["cite_001"])

    def test_build_synthesis_uses_distinct_counter_and_minority_criteria(self):
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
                "source_id": "minority_macro_letter",
                "publisher": "Macro Letter",
                "credibility_tier": 3,
                "rank_in_pack": 2,
            },
            {
                "chunk_id": "doc_003_chunk_000",
                "doc_id": "doc_003",
                "source_id": "reuters_business",
                "publisher": "Reuters",
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
                "canonical_url": "https://example.test/minority",
                "title": "Minority view still expects a hard landing",
                "published_at": "2026-03-10T15:00:00Z",
                "fetched_at": "2026-03-10T15:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "A minority of strategists still expects a hard landing.",
            },
            "doc_003": {
                "canonical_url": "https://example.test/counter",
                "title": "Investors challenge the soft-landing narrative",
                "published_at": "2026-03-10T15:15:00Z",
                "fetched_at": "2026-03-10T15:20:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Investors challenge the soft-landing narrative as growth data weakens.",
            },
            "doc_004": {
                "canonical_url": "https://example.test/bls",
                "title": "Watch payroll revisions next week",
                "published_at": "2026-03-10T13:30:00Z",
                "fetched_at": "2026-03-10T13:35:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Watch payroll revisions next week for confirmation.",
            },
        }
        chunks_by_id = {
            "doc_001_chunk_000": {"text": "Fed keeps policy steady while inflation progress is uneven."},
            "doc_002_chunk_000": {"text": "A minority of strategists still expects a hard landing."},
            "doc_003_chunk_000": {"text": "Investors challenge the soft-landing narrative as growth data weakens."},
            "doc_004_chunk_000": {"text": "Watch payroll revisions next week for confirmation."},
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

        self.assertEqual(synthesis["prevailing"][0]["citation_ids"], ["cite_001"])
        self.assertEqual(synthesis["counter"][0]["citation_ids"], ["cite_003"])
        self.assertEqual(synthesis["minority"][0]["citation_ids"], ["cite_002"])
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
