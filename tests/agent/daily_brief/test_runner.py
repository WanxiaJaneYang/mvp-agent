import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import get_args, get_type_hints

from apps.agent.daily_brief.runner import (
    build_daily_brief_query,
    prepare_daily_brief_inputs,
    build_daily_brief_corpus,
    build_daily_brief_synthesis,
    load_active_fixture_payloads,
    run_fixture_daily_brief,
)
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
