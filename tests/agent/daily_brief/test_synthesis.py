import unittest

from apps.agent.daily_brief.synthesis import (
    SynthesisRetryPlan,
    build_changed_section,
    build_citation_store,
    build_synthesis,
)


class DailyBriefSynthesisTests(unittest.TestCase):
    def test_build_synthesis_emits_multiple_bullets_per_section_when_evidence_supports_it(self):
        evidence_items = [
            {
                "chunk_id": "doc_prevailing_a_chunk_000",
                "doc_id": "doc_prevailing_a",
                "source_id": "fed_press_releases",
                "publisher": "Federal Reserve",
                "credibility_tier": 1,
                "rank_in_pack": 1,
            },
            {
                "chunk_id": "doc_prevailing_b_chunk_000",
                "doc_id": "doc_prevailing_b",
                "source_id": "us_bls_news",
                "publisher": "BLS",
                "credibility_tier": 1,
                "rank_in_pack": 2,
            },
            {
                "chunk_id": "doc_counter_a_chunk_000",
                "doc_id": "doc_counter_a",
                "source_id": "reuters_business",
                "publisher": "Reuters",
                "credibility_tier": 2,
                "rank_in_pack": 3,
            },
            {
                "chunk_id": "doc_counter_b_chunk_000",
                "doc_id": "doc_counter_b",
                "source_id": "wsj_markets",
                "publisher": "Wall Street Journal",
                "credibility_tier": 2,
                "rank_in_pack": 4,
            },
            {
                "chunk_id": "doc_minority_a_chunk_000",
                "doc_id": "doc_minority_a",
                "source_id": "macro_letter_a",
                "publisher": "Macro Letter",
                "credibility_tier": 3,
                "rank_in_pack": 5,
            },
            {
                "chunk_id": "doc_minority_b_chunk_000",
                "doc_id": "doc_minority_b",
                "source_id": "macro_letter_b",
                "publisher": "Strategy Weekly",
                "credibility_tier": 3,
                "rank_in_pack": 6,
            },
            {
                "chunk_id": "doc_watch_a_chunk_000",
                "doc_id": "doc_watch_a",
                "source_id": "cpi_preview",
                "publisher": "CPI Preview Desk",
                "credibility_tier": 1,
                "rank_in_pack": 7,
            },
            {
                "chunk_id": "doc_watch_b_chunk_000",
                "doc_id": "doc_watch_b",
                "source_id": "jobs_preview",
                "publisher": "Jobs Preview Desk",
                "credibility_tier": 1,
                "rank_in_pack": 8,
            },
        ]
        documents_by_id = {
            "doc_prevailing_a": {
                "canonical_url": "https://example.test/prevailing-a",
                "title": "Fed keeps policy steady",
                "published_at": "2026-03-10T14:00:00Z",
                "fetched_at": "2026-03-10T14:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Fed officials kept policy steady while inflation progress remained uneven.",
            },
            "doc_prevailing_b": {
                "canonical_url": "https://example.test/prevailing-b",
                "title": "Payroll growth remains resilient",
                "published_at": "2026-03-10T13:30:00Z",
                "fetched_at": "2026-03-10T13:35:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Payroll growth remained resilient even as hiring cooled from January's pace.",
            },
            "doc_counter_a": {
                "canonical_url": "https://example.test/counter-a",
                "title": "Bond desks push back on soft landing",
                "published_at": "2026-03-10T12:45:00Z",
                "fetched_at": "2026-03-10T12:50:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Bond desks pushed back on the soft-landing consensus as growth indicators cooled.",
            },
            "doc_counter_b": {
                "canonical_url": "https://example.test/counter-b",
                "title": "Investors question the growth rebound",
                "published_at": "2026-03-10T12:15:00Z",
                "fetched_at": "2026-03-10T12:20:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Investors questioned the expected growth rebound after weaker survey data.",
            },
            "doc_minority_a": {
                "canonical_url": "https://example.test/minority-a",
                "title": "Minority view sees reacceleration risk",
                "published_at": "2026-03-10T11:45:00Z",
                "fetched_at": "2026-03-10T11:50:00Z",
                "paywall_policy": "full",
                "rss_snippet": "A minority of strategists still sees inflation reacceleration risk this spring.",
            },
            "doc_minority_b": {
                "canonical_url": "https://example.test/minority-b",
                "title": "Contrarian desks expect a sharper slowdown",
                "published_at": "2026-03-10T11:15:00Z",
                "fetched_at": "2026-03-10T11:20:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Contrarian desks expect a sharper slowdown than consensus forecasts imply.",
            },
            "doc_watch_a": {
                "canonical_url": "https://example.test/watch-a",
                "title": "Watch CPI shelter prints",
                "published_at": "2026-03-10T10:45:00Z",
                "fetched_at": "2026-03-10T10:50:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Watch the next CPI shelter prints for confirmation that disinflation is broadening.",
            },
            "doc_watch_b": {
                "canonical_url": "https://example.test/watch-b",
                "title": "Monitor payroll revisions",
                "published_at": "2026-03-10T10:15:00Z",
                "fetched_at": "2026-03-10T10:20:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Monitor payroll revisions next week for confirmation that labor demand is cooling.",
            },
        }
        chunks_by_id = {
            "doc_prevailing_a_chunk_000": {"text": "Fed officials kept policy steady while inflation progress remained uneven."},
            "doc_prevailing_b_chunk_000": {"text": "Payroll growth remained resilient even as hiring cooled from January's pace."},
            "doc_counter_a_chunk_000": {"text": "Bond desks pushed back on the soft-landing consensus as growth indicators cooled."},
            "doc_counter_b_chunk_000": {"text": "Investors questioned the expected growth rebound after weaker survey data."},
            "doc_minority_a_chunk_000": {"text": "A minority of strategists still sees inflation reacceleration risk this spring."},
            "doc_minority_b_chunk_000": {"text": "Contrarian desks expect a sharper slowdown than consensus forecasts imply."},
            "doc_watch_a_chunk_000": {"text": "Watch the next CPI shelter prints for confirmation that disinflation is broadening."},
            "doc_watch_b_chunk_000": {"text": "Monitor payroll revisions next week for confirmation that labor demand is cooling."},
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

        self.assertEqual(len(synthesis["prevailing"]), 2)
        self.assertEqual(len(synthesis["counter"]), 2)
        self.assertEqual(len(synthesis["minority"]), 2)
        self.assertEqual(len(synthesis["watch"]), 2)
        self.assertEqual(
            synthesis["prevailing"][0]["citation_ids"] + synthesis["prevailing"][1]["citation_ids"],
            ["cite_001", "cite_002"],
        )
        self.assertEqual(
            synthesis["counter"][0]["citation_ids"] + synthesis["counter"][1]["citation_ids"],
            ["cite_003", "cite_004"],
        )

    def test_build_synthesis_uses_section_specific_bullet_language(self):
        evidence_items = [
            {
                "chunk_id": "doc_prevailing_chunk_000",
                "doc_id": "doc_prevailing",
                "source_id": "fed_press_releases",
                "publisher": "Federal Reserve",
                "credibility_tier": 1,
                "rank_in_pack": 1,
            },
            {
                "chunk_id": "doc_counter_chunk_000",
                "doc_id": "doc_counter",
                "source_id": "reuters_business",
                "publisher": "Reuters",
                "credibility_tier": 2,
                "rank_in_pack": 2,
            },
            {
                "chunk_id": "doc_minority_chunk_000",
                "doc_id": "doc_minority",
                "source_id": "macro_letter",
                "publisher": "Macro Letter",
                "credibility_tier": 3,
                "rank_in_pack": 3,
            },
            {
                "chunk_id": "doc_watch_chunk_000",
                "doc_id": "doc_watch",
                "source_id": "bls_preview",
                "publisher": "BLS Preview Desk",
                "credibility_tier": 1,
                "rank_in_pack": 4,
            },
        ]
        documents_by_id = {
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
                "title": "Investors question the growth rebound",
                "published_at": "2026-03-10T13:00:00Z",
                "fetched_at": "2026-03-10T13:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Investors questioned the expected growth rebound after weaker survey data.",
            },
            "doc_minority": {
                "canonical_url": "https://example.test/minority",
                "title": "Minority view sees reacceleration risk",
                "published_at": "2026-03-10T12:00:00Z",
                "fetched_at": "2026-03-10T12:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "A minority of strategists still sees inflation reacceleration risk this spring.",
            },
            "doc_watch": {
                "canonical_url": "https://example.test/watch",
                "title": "Watch CPI shelter prints",
                "published_at": "2026-03-10T11:00:00Z",
                "fetched_at": "2026-03-10T11:05:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Watch the next CPI shelter prints for confirmation that disinflation is broadening.",
            },
        }
        chunks_by_id = {
            "doc_prevailing_chunk_000": {"text": "Fed officials kept policy steady while inflation progress remained uneven."},
            "doc_counter_chunk_000": {"text": "Investors questioned the expected growth rebound after weaker survey data."},
            "doc_minority_chunk_000": {"text": "A minority of strategists still sees inflation reacceleration risk this spring."},
            "doc_watch_chunk_000": {"text": "Watch the next CPI shelter prints for confirmation that disinflation is broadening."},
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

        self.assertEqual(
            synthesis["prevailing"][0]["text"],
            "Fed officials kept policy steady while inflation progress remained uneven.",
        )
        self.assertEqual(
            synthesis["counter"][0]["text"],
            "Counterpoint: Investors question the growth rebound.",
        )
        self.assertEqual(
            synthesis["minority"][0]["text"],
            "Minority view: A minority of strategists still sees inflation reacceleration risk this spring.",
        )
        self.assertEqual(
            synthesis["watch"][0]["text"],
            "Watch: CPI shelter prints.",
        )

    def test_build_changed_section_uses_current_cited_bullets_when_sections_shift(self):
        changed = build_changed_section(
            current_synthesis={
                "prevailing": [{"text": "Fed kept policy steady (Federal Reserve).", "citation_ids": ["cite_001"], "confidence_label": "high"}],
                "counter": [{"text": "Growth is cooling faster (Reuters).", "citation_ids": ["cite_002"], "confidence_label": "medium"}],
                "minority": [{"text": "Some investors expect a rebound (WSJ).", "citation_ids": ["cite_003"], "confidence_label": "medium"}],
                "watch": [{"text": "Watch payroll revisions next week.", "citation_ids": ["cite_004"], "confidence_label": "high"}],
            },
            previous_synthesis={
                "prevailing": [{"text": "Inflation stayed sticky yesterday.", "citation_ids": ["cite_old_001"]}],
                "counter": [{"text": "Growth is cooling faster (Reuters).", "citation_ids": ["cite_old_002"]}],
                "watch": [{"text": "[Insufficient evidence to produce a validated output]", "citation_ids": []}],
            },
        )

        self.assertEqual(len(changed), 3)
        self.assertEqual(changed[0]["citation_ids"], ["cite_001"])
        self.assertIn("Prevailing changed versus yesterday", changed[0]["text"])
        self.assertEqual(changed[1]["citation_ids"], ["cite_003"])
        self.assertIn("Minority is newly supported today", changed[1]["text"])
        self.assertEqual(changed[2]["citation_ids"], ["cite_004"])
        self.assertIn("Watch gained support today", changed[2]["text"])

    def test_build_synthesis_retry_plan_reassigns_failed_section_with_alternate_evidence(self):
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
                "chunk_id": "doc_counter_invalid_chunk_000",
                "doc_id": "doc_counter_invalid",
                "source_id": "reuters_business",
                "publisher": "Reuters",
                "credibility_tier": 2,
                "rank_in_pack": 4,
            },
            {
                "chunk_id": "doc_counter_retry_chunk_000",
                "doc_id": "doc_counter_retry",
                "source_id": "wsj_markets",
                "publisher": "Wall Street Journal",
                "credibility_tier": 2,
                "rank_in_pack": 5,
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
            "doc_counter_invalid": {
                "canonical_url": "https://example.test/counter-invalid",
                "title": "Bond traders push back on soft-landing consensus",
                "published_at": None,
                "fetched_at": "2026-03-10T14:35:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Bond traders push back on the soft-landing consensus as growth cools.",
            },
            "doc_counter_retry": {
                "canonical_url": "https://example.test/counter-retry",
                "title": "Investors question the soft-landing narrative",
                "published_at": "2026-03-10T14:20:00Z",
                "fetched_at": "2026-03-10T14:25:00Z",
                "paywall_policy": "full",
                "rss_snippet": "Investors question the soft-landing narrative as growth data weakens.",
            },
        }
        chunks_by_id = {
            "doc_watch_chunk_000": {"text": "Watch Friday CPI for shelter inflation surprises."},
            "doc_minority_chunk_000": {"text": "A minority of investors still expects inflation to reaccelerate."},
            "doc_prevailing_chunk_000": {"text": "Fed officials kept policy steady while inflation progress remained uneven."},
            "doc_counter_invalid_chunk_000": {"text": "Bond traders push back on the soft-landing consensus as growth cools."},
            "doc_counter_retry_chunk_000": {"text": "Investors question the soft-landing narrative as growth data weakens."},
        }

        citations = build_citation_store(
            evidence_items=evidence_items,
            documents_by_id=documents_by_id,
            chunks_by_id=chunks_by_id,
        )
        first_attempt = build_synthesis(
            evidence_items=evidence_items,
            documents_by_id=documents_by_id,
            citation_store=citations,
        )
        retry_attempt = build_synthesis(
            evidence_items=evidence_items,
            documents_by_id=documents_by_id,
            citation_store=citations,
            retry_plan=SynthesisRetryPlan(
                pinned_chunk_ids_by_section={
                    "prevailing": "doc_prevailing_chunk_000",
                    "minority": "doc_minority_chunk_000",
                    "watch": "doc_watch_chunk_000",
                },
                target_sections=("counter",),
                blocked_chunk_ids=frozenset({"doc_counter_invalid_chunk_000"}),
            ),
        )

        self.assertEqual(first_attempt["counter"][0]["citation_ids"], ["cite_004"])
        self.assertEqual(retry_attempt["counter"][0]["citation_ids"], ["cite_005"])
        self.assertEqual(retry_attempt["prevailing"][0]["citation_ids"], ["cite_003"])
        self.assertEqual(retry_attempt["minority"][0]["citation_ids"], ["cite_002"])
        self.assertEqual(retry_attempt["watch"][0]["citation_ids"], ["cite_001"])
        self.assertNotIn("meta", retry_attempt)

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
