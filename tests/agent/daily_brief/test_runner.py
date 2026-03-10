import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import get_args, get_type_hints
from unittest.mock import patch

from apps.agent.daily_brief.runner import (
    build_daily_brief_query,
    prepare_daily_brief_inputs,
    build_daily_brief_corpus,
    build_daily_brief_synthesis,
    load_active_fixture_payloads,
    load_active_live_payloads,
    run_daily_brief,
    run_fixture_daily_brief,
)
from apps.agent.daily_brief.synthesis import build_citation_store
from apps.agent.pipeline.types import (
    BulletCitationRow,
    CitationStoreEntry,
    CitationValidationResult,
    DailyBriefCorpusStageData,
    DailyBriefInputStageData,
    DailyBriefSectionBulletRow,
    DailyBriefSynthesisStageData,
    EvidencePackItem,
    FinalSynthesisResult,
    FtsRow,
    PlannedFetchItem,
    RunContext,
    RunStatus,
    RunType,
    RuntimeChunkRow,
    RuntimeDocumentRecord,
    SourceRegistryEntry,
    SourceRow,
)
from apps.agent.runtime.budget_guard import BudgetCaps
from apps.agent.runtime.cost_ledger import BudgetWindowSnapshot


class DailyBriefRunnerTests(unittest.TestCase):
    def test_build_daily_brief_synthesis_retry_reassigns_failed_section_without_retry_metadata(self):
        stage_data = DailyBriefCorpusStageData(
            source_rows=[],
            documents=[
                {
                    "source_id": "bls_preview",
                    "publisher": "BLS Preview Desk",
                    "canonical_url": "https://example.test/watch",
                    "title": "Watch Friday CPI for shelter inflation",
                    "author": None,
                    "language": "en",
                    "doc_type": "analysis",
                    "published_at": "2026-03-10T16:00:00Z",
                    "fetched_at": "2026-03-10T16:05:00Z",
                    "paywall_policy": "full",
                    "metadata_only": 0,
                    "rss_snippet": "Markets are watching Friday CPI for shelter inflation surprises.",
                    "body_text": "Watch Friday CPI for shelter inflation surprises.",
                    "content_hash": "hash_watch",
                    "status": "active",
                    "created_at": "2026-03-10T16:05:00Z",
                    "updated_at": "2026-03-10T16:05:00Z",
                    "doc_id": "doc_watch",
                    "credibility_tier": 1,
                    "ingestion_run_id": "run_retry_real",
                },
                {
                    "source_id": "market_commentary",
                    "publisher": "Market Commentary",
                    "canonical_url": "https://example.test/minority",
                    "title": "Minority view still expects a hard landing",
                    "author": None,
                    "language": "en",
                    "doc_type": "analysis",
                    "published_at": "2026-03-10T15:30:00Z",
                    "fetched_at": "2026-03-10T15:35:00Z",
                    "paywall_policy": "full",
                    "metadata_only": 0,
                    "rss_snippet": "A minority of investors still expects a hard landing.",
                    "body_text": "A minority of investors still expects a hard landing.",
                    "content_hash": "hash_minority",
                    "status": "active",
                    "created_at": "2026-03-10T15:35:00Z",
                    "updated_at": "2026-03-10T15:35:00Z",
                    "doc_id": "doc_minority",
                    "credibility_tier": 3,
                    "ingestion_run_id": "run_retry_real",
                },
                {
                    "source_id": "fed_press_releases",
                    "publisher": "Federal Reserve",
                    "canonical_url": "https://example.test/prevailing",
                    "title": "Fed keeps policy steady",
                    "author": None,
                    "language": "en",
                    "doc_type": "statement",
                    "published_at": "2026-03-10T14:00:00Z",
                    "fetched_at": "2026-03-10T14:05:00Z",
                    "paywall_policy": "full",
                    "metadata_only": 0,
                    "rss_snippet": "Fed officials kept policy steady while inflation progress remained uneven.",
                    "body_text": "Fed officials kept policy steady while inflation progress remained uneven.",
                    "content_hash": "hash_prevailing",
                    "status": "active",
                    "created_at": "2026-03-10T14:05:00Z",
                    "updated_at": "2026-03-10T14:05:00Z",
                    "doc_id": "doc_prevailing",
                    "credibility_tier": 1,
                    "ingestion_run_id": "run_retry_real",
                },
                {
                    "source_id": "reuters_business",
                    "publisher": "Reuters",
                    "canonical_url": "https://example.test/counter-invalid",
                    "title": "Bond traders push back on soft-landing consensus",
                    "author": None,
                    "language": "en",
                    "doc_type": "news",
                    "published_at": None,
                    "fetched_at": "2026-03-10T14:35:00Z",
                    "paywall_policy": "full",
                    "metadata_only": 0,
                    "rss_snippet": "Bond traders push back on the soft-landing consensus as growth cools.",
                    "body_text": "Bond traders push back on the soft-landing consensus as growth cools.",
                    "content_hash": "hash_counter_invalid",
                    "status": "active",
                    "created_at": "2026-03-10T14:35:00Z",
                    "updated_at": "2026-03-10T14:35:00Z",
                    "doc_id": "doc_counter_invalid",
                    "credibility_tier": 2,
                    "ingestion_run_id": "run_retry_real",
                },
                {
                    "source_id": "wsj_markets",
                    "publisher": "Wall Street Journal",
                    "canonical_url": "https://example.test/counter-retry",
                    "title": "Investors question the soft-landing narrative",
                    "author": None,
                    "language": "en",
                    "doc_type": "news",
                    "published_at": "2026-03-10T14:20:00Z",
                    "fetched_at": "2026-03-10T14:25:00Z",
                    "paywall_policy": "full",
                    "metadata_only": 0,
                    "rss_snippet": "Investors question the soft-landing narrative as growth data weakens.",
                    "body_text": "Investors question the soft-landing narrative as growth data weakens.",
                    "content_hash": "hash_counter_retry",
                    "status": "active",
                    "created_at": "2026-03-10T14:25:00Z",
                    "updated_at": "2026-03-10T14:25:00Z",
                    "doc_id": "doc_counter_retry",
                    "credibility_tier": 2,
                    "ingestion_run_id": "run_retry_real",
                },
            ],
            chunks=[
                {"chunk_id": "doc_watch_chunk_000", "doc_id": "doc_watch", "chunk_index": 0, "text": "Watch Friday CPI for shelter inflation surprises.", "token_count": 6, "char_start": 0, "char_end": 43, "created_at": "2026-03-10T16:05:00Z"},
                {"chunk_id": "doc_minority_chunk_000", "doc_id": "doc_minority", "chunk_index": 0, "text": "A minority of investors still expects a hard landing.", "token_count": 9, "char_start": 0, "char_end": 55, "created_at": "2026-03-10T15:35:00Z"},
                {"chunk_id": "doc_prevailing_chunk_000", "doc_id": "doc_prevailing", "chunk_index": 0, "text": "Fed officials kept policy steady while inflation progress remained uneven.", "token_count": 10, "char_start": 0, "char_end": 71, "created_at": "2026-03-10T14:05:00Z"},
                {"chunk_id": "doc_counter_invalid_chunk_000", "doc_id": "doc_counter_invalid", "chunk_index": 0, "text": "Bond traders push back on the soft-landing consensus as growth cools.", "token_count": 10, "char_start": 0, "char_end": 70, "created_at": "2026-03-10T14:35:00Z"},
                {"chunk_id": "doc_counter_retry_chunk_000", "doc_id": "doc_counter_retry", "chunk_index": 0, "text": "Investors question the soft-landing narrative as growth data weakens.", "token_count": 9, "char_start": 0, "char_end": 68, "created_at": "2026-03-10T14:25:00Z"},
            ],
            fts_rows=[
                {"text": "Watch Friday CPI for shelter inflation surprises.", "doc_id": "doc_watch", "chunk_id": "doc_watch_chunk_000", "publisher": "BLS Preview Desk", "source_id": "bls_preview", "published_at": "2026-03-10T16:00:00Z", "credibility_tier": 1},
                {"text": "A minority of investors still expects a hard landing.", "doc_id": "doc_minority", "chunk_id": "doc_minority_chunk_000", "publisher": "Market Commentary", "source_id": "market_commentary", "published_at": "2026-03-10T15:30:00Z", "credibility_tier": 3},
                {"text": "Fed officials kept policy steady while inflation progress remained uneven.", "doc_id": "doc_prevailing", "chunk_id": "doc_prevailing_chunk_000", "publisher": "Federal Reserve", "source_id": "fed_press_releases", "published_at": "2026-03-10T14:00:00Z", "credibility_tier": 1},
                {"text": "Bond traders push back on the soft-landing consensus as growth cools.", "doc_id": "doc_counter_invalid", "chunk_id": "doc_counter_invalid_chunk_000", "publisher": "Reuters", "source_id": "reuters_business", "published_at": None, "credibility_tier": 2},
                {"text": "Investors question the soft-landing narrative as growth data weakens.", "doc_id": "doc_counter_retry", "chunk_id": "doc_counter_retry_chunk_000", "publisher": "Wall Street Journal", "source_id": "wsj_markets", "published_at": "2026-03-10T14:20:00Z", "credibility_tier": 2},
            ],
        )
        registry = {
            "bls_preview": {"id": "bls_preview", "name": "BLS Preview Desk", "url": "https://example.test/watch", "type": "rss", "credibility_tier": 1, "paywall_policy": "full", "fetch_interval": "daily", "tags": ["macro_data"]},
            "market_commentary": {"id": "market_commentary", "name": "Market Commentary", "url": "https://example.test/minority", "type": "rss", "credibility_tier": 3, "paywall_policy": "full", "fetch_interval": "daily", "tags": ["market_narrative"]},
            "fed_press_releases": {"id": "fed_press_releases", "name": "Federal Reserve", "url": "https://example.test/prevailing", "type": "rss", "credibility_tier": 1, "paywall_policy": "full", "fetch_interval": "daily", "tags": ["policy_centralbank"]},
            "reuters_business": {"id": "reuters_business", "name": "Reuters", "url": "https://example.test/counter-invalid", "type": "rss", "credibility_tier": 2, "paywall_policy": "full", "fetch_interval": "daily", "tags": ["market_narrative"]},
            "wsj_markets": {"id": "wsj_markets", "name": "Wall Street Journal", "url": "https://example.test/counter-retry", "type": "rss", "credibility_tier": 2, "paywall_policy": "full", "fetch_interval": "daily", "tags": ["market_narrative"]},
        }

        with patch("apps.agent.daily_brief.runner.build_evidence_pack_report") as evidence_pack_report_mock:
            evidence_pack_report_mock.return_value = {
                "items": [
                    {"chunk_id": "doc_watch_chunk_000", "source_id": "bls_preview", "publisher": "BLS Preview Desk", "credibility_tier": 1, "retrieval_score": 0.95, "semantic_score": 0.95, "recency_score": 0.90, "credibility_score": 1.0, "rank_in_pack": 1},
                    {"chunk_id": "doc_minority_chunk_000", "source_id": "market_commentary", "publisher": "Market Commentary", "credibility_tier": 3, "retrieval_score": 0.90, "semantic_score": 0.90, "recency_score": 0.80, "credibility_score": 0.6, "rank_in_pack": 2},
                    {"chunk_id": "doc_prevailing_chunk_000", "source_id": "fed_press_releases", "publisher": "Federal Reserve", "credibility_tier": 1, "retrieval_score": 0.88, "semantic_score": 0.88, "recency_score": 0.70, "credibility_score": 1.0, "rank_in_pack": 3},
                    {"chunk_id": "doc_counter_invalid_chunk_000", "source_id": "reuters_business", "publisher": "Reuters", "credibility_tier": 2, "retrieval_score": 0.86, "semantic_score": 0.86, "recency_score": 0.68, "credibility_score": 0.8, "rank_in_pack": 4},
                    {"chunk_id": "doc_counter_retry_chunk_000", "source_id": "wsj_markets", "publisher": "Wall Street Journal", "credibility_tier": 2, "retrieval_score": 0.84, "semantic_score": 0.84, "recency_score": 0.66, "credibility_score": 0.8, "rank_in_pack": 5},
                ],
                "diversity_stats": {"unique_publishers": 5},
                "diversity_check": "pass",
                "notes": [],
            }

            synthesis = build_daily_brief_synthesis(
                stage_data=stage_data,
                registry=registry,
                run_id="run_retry_real",
            )

        self.assertEqual(synthesis.stage8_result["status"], "ok")
        self.assertEqual(synthesis.stage8_result["validation_attempts"], 2)
        self.assertFalse(synthesis.stage8_result["retry_exhausted"])
        self.assertEqual(synthesis.final_result["synthesis"]["counter"][0]["citation_ids"], ["cite_005"])
        self.assertNotIn("meta", synthesis.final_result["synthesis"])

    def test_build_daily_brief_synthesis_retries_once_before_returning_validated_output(self):
        stage_inputs = prepare_daily_brief_inputs(generated_at_utc="2026-03-10T16:00:00Z")
        context = RunContext(
            run_id="run_daily_fixture",
            run_type=RunType.DAILY_BRIEF,
            started_at="2026-03-10T16:00:00Z",
            status=RunStatus.RUNNING,
        )
        corpus = build_daily_brief_corpus(
            stage_data=stage_inputs,
            run_id="run_daily_fixture",
            context=context,
        )
        first_attempt = {
            "prevailing": [{"text": "First attempt prevailing.", "citation_ids": ["cite_001"]}],
            "counter": [],
            "minority": [],
            "watch": [],
        }
        retried_attempt = {
            "prevailing": [{"text": "Retried prevailing.", "citation_ids": ["cite_001"]}],
            "counter": [{"text": "Retried counter.", "citation_ids": ["cite_002"]}],
            "minority": [{"text": "Retried minority.", "citation_ids": ["cite_003"]}],
            "watch": [{"text": "Retried watch.", "citation_ids": ["cite_004"]}],
        }
        citation_store = {
            "cite_001": {"citation_id": "cite_001", "source_id": "src1", "publisher": "Pub 1", "doc_id": "doc_001", "chunk_id": "chunk_001", "url": "https://example.test/1", "title": "Doc 1", "published_at": "2026-03-10T10:00:00Z", "fetched_at": "2026-03-10T10:05:00Z", "paywall_policy": "full", "quote_text": "Quote 1", "snippet_text": "Snippet 1"},
            "cite_002": {"citation_id": "cite_002", "source_id": "src2", "publisher": "Pub 2", "doc_id": "doc_002", "chunk_id": "chunk_002", "url": "https://example.test/2", "title": "Doc 2", "published_at": "2026-03-10T11:00:00Z", "fetched_at": "2026-03-10T11:05:00Z", "paywall_policy": "full", "quote_text": "Quote 2", "snippet_text": "Snippet 2"},
            "cite_003": {"citation_id": "cite_003", "source_id": "src3", "publisher": "Pub 3", "doc_id": "doc_003", "chunk_id": "chunk_003", "url": "https://example.test/3", "title": "Doc 3", "published_at": "2026-03-10T12:00:00Z", "fetched_at": "2026-03-10T12:05:00Z", "paywall_policy": "full", "quote_text": "Quote 3", "snippet_text": "Snippet 3"},
            "cite_004": {"citation_id": "cite_004", "source_id": "src4", "publisher": "Pub 4", "doc_id": "doc_004", "chunk_id": "chunk_004", "url": "https://example.test/4", "title": "Doc 4", "published_at": "2026-03-10T13:00:00Z", "fetched_at": "2026-03-10T13:05:00Z", "paywall_policy": "full", "quote_text": "Quote 4", "snippet_text": "Snippet 4"},
        }

        with patch("apps.agent.daily_brief.runner.build_synthesis") as build_synthesis_mock, patch(
            "apps.agent.daily_brief.runner.run_stage8_citation_validation"
        ) as validation_mock:
            build_synthesis_mock.side_effect = [first_attempt, retried_attempt]
            validation_mock.side_effect = [
                {
                    "status": "retry",
                    "synthesis": first_attempt,
                    "citation_store": citation_store,
                    "report": {
                        "removed_bullets": 4,
                        "empty_core_sections": ["counter", "minority", "watch"],
                        "total_bullets": 1,
                        "cited_bullets": 1,
                        "validation_passed": False,
                        "should_retry": True,
                        "synthesis": first_attempt,
                        "citation_store": citation_store,
                    },
                },
                {
                    "status": "ok",
                    "synthesis": retried_attempt,
                    "citation_store": citation_store,
                    "report": {
                        "removed_bullets": 0,
                        "empty_core_sections": [],
                        "total_bullets": 4,
                        "cited_bullets": 4,
                        "validation_passed": True,
                        "should_retry": False,
                        "synthesis": retried_attempt,
                        "citation_store": citation_store,
                    },
                },
            ]

            synthesis = build_daily_brief_synthesis(
                stage_data=corpus,
                registry=stage_inputs.registry,
                run_id="run_daily_fixture",
            )

        self.assertEqual(validation_mock.call_count, 2)
        self.assertIsNone(build_synthesis_mock.call_args_list[0].kwargs["retry_plan"])
        self.assertIsNotNone(build_synthesis_mock.call_args_list[1].kwargs["retry_plan"])
        self.assertEqual(synthesis.stage8_result["validation_attempts"], 2)
        self.assertEqual(synthesis.stage8_result["max_validation_attempts"], 2)
        self.assertFalse(synthesis.stage8_result["retry_exhausted"])
        self.assertEqual(synthesis.final_result["status"], "ok")

    def test_build_daily_brief_synthesis_abstains_after_retry_exhaustion(self):
        stage_inputs = prepare_daily_brief_inputs(generated_at_utc="2026-03-10T16:00:00Z")
        context = RunContext(
            run_id="run_daily_fixture",
            run_type=RunType.DAILY_BRIEF,
            started_at="2026-03-10T16:00:00Z",
            status=RunStatus.RUNNING,
        )
        corpus = build_daily_brief_corpus(
            stage_data=stage_inputs,
            run_id="run_daily_fixture",
            context=context,
        )
        first_attempt = {
            "prevailing": [{"text": "First attempt prevailing.", "citation_ids": ["cite_001"]}],
            "counter": [],
            "minority": [],
            "watch": [],
        }
        second_attempt = {
            "prevailing": [],
            "counter": [],
            "minority": [],
            "watch": [],
        }

        with patch("apps.agent.daily_brief.runner.build_synthesis") as build_synthesis_mock, patch(
            "apps.agent.daily_brief.runner.run_stage8_citation_validation"
        ) as validation_mock:
            build_synthesis_mock.side_effect = [first_attempt, second_attempt]
            validation_mock.side_effect = [
                {
                    "status": "retry",
                    "synthesis": first_attempt,
                    "citation_store": {},
                    "report": {
                        "removed_bullets": 4,
                        "empty_core_sections": ["counter", "minority", "watch"],
                        "total_bullets": 1,
                        "cited_bullets": 1,
                        "validation_passed": False,
                        "should_retry": True,
                        "synthesis": first_attempt,
                        "citation_store": {},
                    },
                },
                {
                    "status": "retry",
                    "synthesis": second_attempt,
                    "citation_store": {},
                    "report": {
                        "removed_bullets": 4,
                        "empty_core_sections": ["prevailing", "counter", "minority", "watch"],
                        "total_bullets": 0,
                        "cited_bullets": 0,
                        "validation_passed": False,
                        "should_retry": True,
                        "synthesis": second_attempt,
                        "citation_store": {},
                    },
                },
            ]

            synthesis = build_daily_brief_synthesis(
                stage_data=corpus,
                registry=stage_inputs.registry,
                run_id="run_daily_fixture",
            )

        self.assertEqual(validation_mock.call_count, 2)
        self.assertEqual(synthesis.stage8_result["status"], "retry")
        self.assertEqual(synthesis.stage8_result["validation_attempts"], 2)
        self.assertEqual(synthesis.stage8_result["max_validation_attempts"], 2)
        self.assertTrue(synthesis.stage8_result["retry_exhausted"])
        self.assertEqual(synthesis.final_result["status"], "abstained")
        self.assertEqual(synthesis.final_result["abstain_reason"], "validation_retry_exhausted")

    def test_stage_payload_annotations_use_named_contract_types(self):
        input_hints = get_type_hints(DailyBriefInputStageData)
        corpus_hints = get_type_hints(DailyBriefCorpusStageData)
        synthesis_hints = get_type_hints(DailyBriefSynthesisStageData)

        self.assertEqual(get_args(input_hints["registry"])[1], SourceRegistryEntry)
        self.assertEqual(get_args(input_hints["active_sources"])[0], SourceRegistryEntry)
        self.assertEqual(get_args(input_hints["planned_items"])[0], PlannedFetchItem)
        self.assertEqual(get_args(input_hints["source_rows"])[0], SourceRow)

        self.assertEqual(get_args(corpus_hints["source_rows"])[0], SourceRow)
        self.assertEqual(get_args(corpus_hints["documents"])[0], RuntimeDocumentRecord)
        self.assertEqual(get_args(corpus_hints["chunks"])[0], RuntimeChunkRow)
        self.assertEqual(get_args(corpus_hints["fts_rows"])[0], FtsRow)

        self.assertEqual(get_args(synthesis_hints["evidence_pack_items"])[0], EvidencePackItem)
        self.assertEqual(get_args(synthesis_hints["citation_store"])[1], CitationStoreEntry)
        self.assertIs(synthesis_hints["stage8_result"], CitationValidationResult)
        self.assertIs(synthesis_hints["final_result"], FinalSynthesisResult)
        self.assertEqual(get_args(synthesis_hints["citation_rows"])[0], CitationStoreEntry)
        self.assertEqual(get_args(synthesis_hints["synthesis_bullet_rows"])[0], DailyBriefSectionBulletRow)
        self.assertEqual(get_args(synthesis_hints["bullet_citation_rows"])[0], BulletCitationRow)

    def test_prepare_daily_brief_inputs_returns_typed_stage_payload(self):
        stage_data = prepare_daily_brief_inputs(generated_at_utc="2026-03-10T16:00:00Z")

        self.assertIsInstance(stage_data, DailyBriefInputStageData)
        self.assertEqual(len(stage_data.active_sources), 5)
        self.assertEqual(len(stage_data.source_rows), len(stage_data.active_sources))
        self.assertGreater(len(stage_data.planned_items), 0)

    def test_prepare_daily_brief_inputs_can_use_live_payloads_for_active_subset(self):
        fixture_payloads = load_active_fixture_payloads()

        with patch("apps.agent.daily_brief.runner.fetch_live_payloads_for_source") as live_fetch_mock:
            live_fetch_mock.side_effect = lambda *, source, fetched_at_utc: fixture_payloads[str(source["id"])]
            stage_data = prepare_daily_brief_inputs(
                generated_at_utc="2026-03-10T16:00:00Z",
                use_live_sources=True,
            )

        self.assertIsInstance(stage_data, DailyBriefInputStageData)
        self.assertEqual(len(stage_data.active_sources), 5)
        self.assertGreater(len(stage_data.planned_items), 0)
        self.assertEqual(stage_data.planned_items[0]["source_id"], "fed_press_releases")

    def test_build_daily_brief_corpus_returns_typed_stage_payload_and_updates_counters(self):
        stage_inputs = prepare_daily_brief_inputs(generated_at_utc="2026-03-10T16:00:00Z")
        context = RunContext(
            run_id="run_daily_fixture",
            run_type=RunType.DAILY_BRIEF,
            started_at="2026-03-10T16:00:00Z",
            status=RunStatus.RUNNING,
        )

        corpus = build_daily_brief_corpus(
            stage_data=stage_inputs,
            run_id="run_daily_fixture",
            context=context,
        )

        self.assertIsInstance(corpus, DailyBriefCorpusStageData)
        self.assertGreater(len(corpus.documents), 0)
        self.assertGreater(len(corpus.chunks), 0)
        self.assertGreater(len(corpus.fts_rows), 0)
        self.assertEqual(context.counters.docs_fetched, len(stage_inputs.planned_items))
        self.assertEqual(context.counters.docs_ingested, len(corpus.documents))
        self.assertEqual(context.counters.chunks_indexed, len(corpus.chunks))

    def test_build_daily_brief_synthesis_returns_typed_stage_payload(self):
        stage_inputs = prepare_daily_brief_inputs(generated_at_utc="2026-03-10T16:00:00Z")
        context = RunContext(
            run_id="run_daily_fixture",
            run_type=RunType.DAILY_BRIEF,
            started_at="2026-03-10T16:00:00Z",
            status=RunStatus.RUNNING,
        )
        corpus = build_daily_brief_corpus(
            stage_data=stage_inputs,
            run_id="run_daily_fixture",
            context=context,
        )

        synthesis = build_daily_brief_synthesis(
            stage_data=corpus,
            registry=stage_inputs.registry,
            run_id="run_daily_fixture",
        )

        self.assertIsInstance(synthesis, DailyBriefSynthesisStageData)
        self.assertTrue(synthesis.query_text)
        self.assertGreater(len(synthesis.evidence_pack_items), 0)
        self.assertIn(synthesis.final_result["status"], {"ok", "abstained"})
        self.assertGreater(len(synthesis.synthesis_bullet_rows), 0)
        self.assertIsInstance(synthesis.final_result["synthesis"]["prevailing"][0], dict)
        self.assertIn("citation_ids", synthesis.final_result["synthesis"]["prevailing"][0])

    def test_load_active_fixture_payloads_filters_to_runtime_subset(self):
        fixture_payloads = {
            "fed_press_releases": [{"url": "https://example.test/fed"}],
            "us_bls_news": [{"url": "https://example.test/bls"}],
            "us_bea_news": [{"url": "https://example.test/bea"}],
            "reuters_business": [{"url": "https://example.test/reuters"}],
            "wsj_markets": [{"url": "https://example.test/wsj"}],
            "ecb_press_releases": [{"url": "https://example.test/ecb"}],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = Path(tmpdir) / "fixture_payloads.json"
            fixture_path.write_text(json.dumps(fixture_payloads), encoding="utf-8")

            loaded = load_active_fixture_payloads(fixture_path=fixture_path)

        self.assertEqual(
            list(loaded.keys()),
            [
                "fed_press_releases",
                "us_bls_news",
                "us_bea_news",
                "reuters_business",
                "wsj_markets",
            ],
        )
        self.assertNotIn("ecb_press_releases", loaded)

    def test_load_active_live_payloads_degrades_source_level_failures(self):
        active_sources = [
            {
                "id": "fed_press_releases",
                "name": "Federal Reserve - Press Releases",
                "url": "https://example.test/fed",
                "type": "rss",
                "credibility_tier": 1,
                "paywall_policy": "full",
                "fetch_interval": "daily",
                "tags": ["policy_centralbank"],
            },
            {
                "id": "us_bls_news",
                "name": "U.S. Bureau of Labor Statistics - News Releases",
                "url": "https://example.test/bls",
                "type": "rss",
                "credibility_tier": 1,
                "paywall_policy": "full",
                "fetch_interval": "daily",
                "tags": ["macro_data"],
            },
        ]

        def side_effect(*, source, fetched_at_utc):
            if source["id"] == "us_bls_news":
                raise ValueError("blocked")
            return [{"url": "https://example.test/fed", "title": "Fed keeps policy steady"}]

        with patch("apps.agent.daily_brief.runner.fetch_live_payloads_for_source") as live_fetch_mock:
            live_fetch_mock.side_effect = side_effect
            loaded = load_active_live_payloads(
                active_sources=active_sources,
                fetched_at_utc="2026-03-10T16:00:00Z",
            )

        self.assertEqual(loaded["fed_press_releases"][0]["title"], "Fed keeps policy steady")
        self.assertEqual(loaded["us_bls_news"], [])

    def test_build_daily_brief_query_uses_repeated_document_terms(self):
        documents = [
            {
                "title": "Fed signals slower balance sheet runoff",
                "rss_snippet": "Fed officials discussed liquidity and runoff pace.",
                "body_text": "Fed runoff liquidity balance sheet policy remains central.",
            },
            {
                "title": "BLS reports softer wage growth",
                "rss_snippet": "Labor market cooling supports slower wage growth.",
                "body_text": "Wage growth cools as labor demand moderates.",
            },
        ]

        query = build_daily_brief_query(documents=documents)

        self.assertIn("fed", query)
        self.assertIn("growth", query)
        self.assertNotIn("slower", query)

    def test_run_fixture_daily_brief_writes_expected_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_fixture_daily_brief(
                base_dir=Path(tmpdir),
                run_id="run_fixture_ok",
                generated_at_utc="2026-03-10T16:00:00Z",
            )

            html_path = Path(result["html_path"])
            decision_record_path = Path(result["decision_record_path"])
            artifact_dir = Path(result["artifact_dir"])

            self.assertEqual(result["status"], "ok")
            self.assertTrue(html_path.exists())
            self.assertTrue(decision_record_path.exists())
            self.assertTrue((artifact_dir / "documents.json").exists())
            self.assertTrue((artifact_dir / "chunks.json").exists())
            self.assertTrue((artifact_dir / "evidence_pack_items.json").exists())
            self.assertTrue((artifact_dir / "synthesis_bullets.json").exists())
            self.assertTrue((artifact_dir / "bullet_citations.json").exists())
            self.assertEqual(result["lifecycle"][0]["status"], "running")
            self.assertEqual(result["lifecycle"][-1]["status"], "ok")
            self.assertIn("Daily Brief", html_path.read_text(encoding="utf-8"))
            citation_rows = json.loads((artifact_dir / "citations.json").read_text(encoding="utf-8"))
            synthesis_payload = json.loads((artifact_dir / "synthesis.json").read_text(encoding="utf-8"))
            synthesis_bullets = json.loads((artifact_dir / "synthesis_bullets.json").read_text(encoding="utf-8"))
            bullet_citations = json.loads((artifact_dir / "bullet_citations.json").read_text(encoding="utf-8"))
            run_summary = json.loads((artifact_dir / "run_summary.json").read_text(encoding="utf-8"))
            self.assertIsInstance(citation_rows, list)
            self.assertEqual(citation_rows[0]["citation_id"], "cite_001")
            self.assertEqual(synthesis_bullets[0]["section"], "prevailing")
            self.assertEqual(
                bullet_citations[0]["citation_id"],
                synthesis_payload["prevailing"][0]["citation_ids"][0],
            )
            self.assertEqual(run_summary["guardrail_checks"]["budget_check"], "pass")
            self.assertIn(run_summary["guardrail_checks"]["diversity_check"], {"pass", "fail"})

    def test_run_daily_brief_writes_expected_artifacts_from_live_payloads(self):
        fixture_payloads = load_active_fixture_payloads()

        with patch("apps.agent.daily_brief.runner.fetch_live_payloads_for_source") as live_fetch_mock, tempfile.TemporaryDirectory() as tmpdir:
            live_fetch_mock.side_effect = lambda *, source, fetched_at_utc: fixture_payloads.get(str(source["id"]), [])
            result = run_daily_brief(
                base_dir=Path(tmpdir),
                run_id="run_live_ok",
                generated_at_utc="2026-03-10T16:00:00Z",
            )

            html_path = Path(result["html_path"])
            artifact_dir = Path(result["artifact_dir"])
            run_summary = json.loads((artifact_dir / "run_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "ok")
            self.assertTrue(html_path.exists())
            self.assertTrue((artifact_dir / "documents.json").exists())
            self.assertEqual(run_summary["docs_fetched"], 5)
            self.assertEqual(result["pipeline_status"], "ok")

    def test_run_fixture_daily_brief_persists_budget_preflight_truthfully(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_fixture_daily_brief(
                base_dir=Path(tmpdir),
                run_id="run_fixture_budget_truth",
                generated_at_utc="2026-03-10T16:00:00Z",
                budget_preflight={
                    "hourly_spend_usd": 0.02,
                    "daily_spend_usd": 0.50,
                    "monthly_spend_usd": 20.0,
                    "next_estimated_cost_usd": 0.01,
                    "caps": BudgetCaps(),
                    "windows": {
                        "hourly": BudgetWindowSnapshot(
                            window_start="2026-03-10T16:00:00Z",
                            window_end="2026-03-10T16:59:59Z",
                            cost_usd=0.02,
                        ),
                        "daily": BudgetWindowSnapshot(
                            window_start="2026-03-10T00:00:00Z",
                            window_end="2026-03-10T23:59:59Z",
                            cost_usd=0.50,
                        ),
                        "monthly": BudgetWindowSnapshot(
                            window_start="2026-03-01T00:00:00Z",
                            window_end="2026-03-31T23:59:59Z",
                            cost_usd=20.0,
                        ),
                    },
                },
            )

            decision_record = json.loads(Path(result["decision_record_path"]).read_text(encoding="utf-8"))
            run_summary = json.loads((Path(result["artifact_dir"]) / "run_summary.json").read_text(encoding="utf-8"))
            html = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertEqual(decision_record["budget_snapshot"]["hourly_spend_usd"], 0.03)
        self.assertEqual(decision_record["budget_snapshot"]["daily_spend_usd"], 0.51)
        self.assertEqual(decision_record["budget_snapshot"]["monthly_spend_usd"], 20.01)
        self.assertTrue(decision_record["budget_snapshot"]["allowed"])
        self.assertEqual(decision_record["guardrail_checks"]["budget_check"], "pass")
        self.assertEqual(run_summary["budget_snapshot"]["hourly_spend_usd"], 0.03)
        self.assertEqual(run_summary["guardrail_checks"]["budget_check"], "pass")
        self.assertIn("Budget: Pass", html)

    def test_run_fixture_daily_brief_reports_retry_attempts_without_double_counting_budget(self):
        first_attempt = {
            "prevailing": [{"text": "First attempt prevailing.", "citation_ids": ["cite_001"]}],
            "counter": [],
            "minority": [],
            "watch": [],
        }
        retried_attempt = {
            "prevailing": [{"text": "Retried prevailing.", "citation_ids": ["cite_001"]}],
            "counter": [{"text": "Retried counter.", "citation_ids": ["cite_002"]}],
            "minority": [{"text": "Retried minority.", "citation_ids": ["cite_003"]}],
            "watch": [{"text": "Retried watch.", "citation_ids": ["cite_004"]}],
        }
        citation_store = {
            "cite_001": {"citation_id": "cite_001", "source_id": "src1", "publisher": "Pub 1", "doc_id": "doc_001", "chunk_id": "chunk_001", "url": "https://example.test/1", "title": "Doc 1", "published_at": "2026-03-10T10:00:00Z", "fetched_at": "2026-03-10T10:05:00Z", "paywall_policy": "full", "quote_text": "Quote 1", "snippet_text": "Snippet 1"},
            "cite_002": {"citation_id": "cite_002", "source_id": "src2", "publisher": "Pub 2", "doc_id": "doc_002", "chunk_id": "chunk_002", "url": "https://example.test/2", "title": "Doc 2", "published_at": "2026-03-10T11:00:00Z", "fetched_at": "2026-03-10T11:05:00Z", "paywall_policy": "full", "quote_text": "Quote 2", "snippet_text": "Snippet 2"},
            "cite_003": {"citation_id": "cite_003", "source_id": "src3", "publisher": "Pub 3", "doc_id": "doc_003", "chunk_id": "chunk_003", "url": "https://example.test/3", "title": "Doc 3", "published_at": "2026-03-10T12:00:00Z", "fetched_at": "2026-03-10T12:05:00Z", "paywall_policy": "full", "quote_text": "Quote 3", "snippet_text": "Snippet 3"},
            "cite_004": {"citation_id": "cite_004", "source_id": "src4", "publisher": "Pub 4", "doc_id": "doc_004", "chunk_id": "chunk_004", "url": "https://example.test/4", "title": "Doc 4", "published_at": "2026-03-10T13:00:00Z", "fetched_at": "2026-03-10T13:05:00Z", "paywall_policy": "full", "quote_text": "Quote 4", "snippet_text": "Snippet 4"},
        }

        with patch("apps.agent.daily_brief.runner.build_synthesis") as build_synthesis_mock, patch(
            "apps.agent.daily_brief.runner.run_stage8_citation_validation"
        ) as validation_mock, tempfile.TemporaryDirectory() as tmpdir:
            build_synthesis_mock.side_effect = [first_attempt, retried_attempt]
            validation_mock.side_effect = [
                {
                    "status": "retry",
                    "synthesis": first_attempt,
                    "citation_store": citation_store,
                    "report": {
                        "removed_bullets": 4,
                        "empty_core_sections": ["counter", "minority", "watch"],
                        "total_bullets": 1,
                        "cited_bullets": 1,
                        "validation_passed": False,
                        "should_retry": True,
                        "synthesis": first_attempt,
                        "citation_store": citation_store,
                    },
                },
                {
                    "status": "ok",
                    "synthesis": retried_attempt,
                    "citation_store": citation_store,
                    "report": {
                        "removed_bullets": 0,
                        "empty_core_sections": [],
                        "total_bullets": 4,
                        "cited_bullets": 4,
                        "validation_passed": True,
                        "should_retry": False,
                        "synthesis": retried_attempt,
                        "citation_store": citation_store,
                    },
                },
            ]
            result = run_fixture_daily_brief(
                base_dir=Path(tmpdir),
                run_id="run_fixture_retry_truth",
                generated_at_utc="2026-03-10T16:00:00Z",
                budget_preflight={
                    "hourly_spend_usd": 0.02,
                    "daily_spend_usd": 0.50,
                    "monthly_spend_usd": 20.0,
                    "next_estimated_cost_usd": 0.01,
                    "caps": BudgetCaps(),
                    "windows": {
                        "hourly": BudgetWindowSnapshot(
                            window_start="2026-03-10T16:00:00Z",
                            window_end="2026-03-10T16:59:59Z",
                            cost_usd=0.02,
                        ),
                        "daily": BudgetWindowSnapshot(
                            window_start="2026-03-10T00:00:00Z",
                            window_end="2026-03-10T23:59:59Z",
                            cost_usd=0.50,
                        ),
                        "monthly": BudgetWindowSnapshot(
                            window_start="2026-03-01T00:00:00Z",
                            window_end="2026-03-31T23:59:59Z",
                            cost_usd=20.0,
                        ),
                    },
                },
            )
            run_summary = json.loads((Path(result["artifact_dir"]) / "run_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(run_summary["validation_attempts"], 2)
        self.assertEqual(run_summary["max_validation_attempts"], 2)
        self.assertFalse(run_summary["validation_retry_exhausted"])
        self.assertEqual(run_summary["budget_snapshot"]["hourly_spend_usd"], 0.03)
        self.assertEqual(run_summary["budget_snapshot"]["daily_spend_usd"], 0.51)
        self.assertEqual(run_summary["budget_snapshot"]["monthly_spend_usd"], 20.01)

    def test_run_fixture_daily_brief_reports_diversity_failure_in_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = Path(tmpdir) / "fixture_payloads.json"
            fixture_path.write_text(
                json.dumps(
                    {
                        "wsj_markets": [
                            {
                                "url": "https://example.test/wsj-only",
                                "title": "Cooling growth draws focus",
                                "published_at": "2026-03-10T15:15:00Z",
                                "fetched_at": "2026-03-10T15:20:00Z",
                                "summary": "Cooling growth becomes the focus.",
                                "doc_type": "news",
                                "language": "en",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_fixture_daily_brief(
                base_dir=Path(tmpdir),
                fixture_path=fixture_path,
                run_id="run_fixture_diversity_fail",
                generated_at_utc="2026-03-10T16:00:00Z",
            )

            decision_record = json.loads(Path(result["decision_record_path"]).read_text(encoding="utf-8"))
            run_summary = json.loads((Path(result["artifact_dir"]) / "run_summary.json").read_text(encoding="utf-8"))
            html = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertEqual(result["status"], "abstained")
        self.assertEqual(decision_record["guardrail_checks"]["diversity_check"], "fail")
        self.assertEqual(run_summary["guardrail_checks"]["diversity_check"], "fail")
        self.assertIn("Diversity: Fail", html)

    def test_run_fixture_daily_brief_stops_before_stage_on_budget_preflight(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_fixture_daily_brief(
                base_dir=Path(tmpdir),
                run_id="run_fixture_budget_stop",
                generated_at_utc="2026-03-10T16:00:00Z",
                budget_preflight={
                    "hourly_spend_usd": 0.09,
                    "daily_spend_usd": 0.50,
                    "monthly_spend_usd": 20.0,
                    "next_estimated_cost_usd": 0.02,
                    "caps": BudgetCaps(),
                    "windows": {
                        "hourly": BudgetWindowSnapshot(
                            window_start="2026-03-10T16:00:00Z",
                            window_end="2026-03-10T16:59:59Z",
                            cost_usd=0.09,
                        ),
                        "daily": BudgetWindowSnapshot(
                            window_start="2026-03-10T00:00:00Z",
                            window_end="2026-03-10T23:59:59Z",
                            cost_usd=0.50,
                        ),
                        "monthly": BudgetWindowSnapshot(
                            window_start="2026-03-01T00:00:00Z",
                            window_end="2026-03-31T23:59:59Z",
                            cost_usd=20.0,
                        ),
                    },
                },
            )

            decision_record = json.loads(Path(result["decision_record_path"]).read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "stopped_budget")
        self.assertEqual(result["pipeline_status"], "stopped_budget")
        self.assertEqual(decision_record["guardrail_checks"]["budget_check"], "fail")
        self.assertFalse(decision_record["budget_snapshot"]["allowed"])
        self.assertIsNone(result["html_path"])

    def test_run_fixture_daily_brief_abstains_when_evidence_is_insufficient(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = Path(tmpdir) / "fixture_payloads.json"
            fixture_path.write_text(
                json.dumps(
                    {
                        "wsj_markets": [
                            {
                                "url": "https://example.test/wsj-only",
                                "title": "Cooling growth draws focus",
                                "published_at": "2026-03-10T15:15:00Z",
                                "fetched_at": "2026-03-10T15:20:00Z",
                                "summary": "Cooling growth becomes the focus.",
                                "doc_type": "news",
                                "language": "en",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_fixture_daily_brief(
                base_dir=Path(tmpdir),
                fixture_path=fixture_path,
                run_id="run_fixture_abstain",
                generated_at_utc="2026-03-10T16:00:00Z",
            )

            html = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertEqual(result["status"], "abstained")
        self.assertIn("Abstained", html)
        self.assertEqual(result["lifecycle"][-1]["status"], "partial")

    def test_script_entrypoint_runs_fixture_slice(self):
        repo_root = Path(__file__).resolve().parents[3]
        script_path = repo_root / "scripts" / "run_daily_brief_fixture.py"

        with tempfile.TemporaryDirectory() as tmpdir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--base-dir",
                    tmpdir,
                    "--run-id",
                    "run_script_entrypoint",
                    "--generated-at-utc",
                    "2026-03-10T16:00:00Z",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            html_path = Path(tmpdir) / "artifacts" / "daily" / "2026-03-10" / "brief.html"
            self.assertTrue(html_path.exists())

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("run_script_entrypoint", completed.stdout)


if __name__ == "__main__":
    unittest.main()
