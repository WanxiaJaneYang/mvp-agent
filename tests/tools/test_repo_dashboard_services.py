from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.repo_dashboard.services.artifact_reader import discover_dashboard_artifacts
from tools.repo_dashboard.services.repo_scan import build_repo_overview
from tools.repo_dashboard.services.status_store import DashboardStatusStore


class DashboardStatusStoreTests(unittest.TestCase):
    def test_bootstraps_empty_state_and_persists_run_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            store = DashboardStatusStore(data_dir=data_dir)

            state = store.load_state()

            self.assertEqual(state["active_run_id"], None)
            self.assertEqual(state["recent_runs"], [])
            self.assertTrue((data_dir / "dashboard_state.json").exists())
            self.assertTrue((data_dir / "runs").exists())

            record = {
                "run_id": "run_fixture_001",
                "run_kind": "fixture",
                "status": "queued",
                "command": ["python", "scripts/run_daily_brief_fixture.py"],
                "started_at_utc": "2026-03-15T09:00:00Z",
                "finished_at_utc": None,
                "exit_code": None,
                "log_path": str(data_dir / "runs" / "run_fixture_001.log"),
                "base_dir": ".tmp_repo_dashboard/demo",
                "artifact_paths": {},
                "publish_decision": None,
                "reason": None,
                "reason_codes": [],
                "summary": None,
            }

            store.upsert_run(record, is_active=True)

            persisted = store.load_state()
            self.assertEqual(persisted["active_run_id"], "run_fixture_001")
            self.assertEqual(len(persisted["recent_runs"]), 1)
            self.assertEqual(store.load_run("run_fixture_001")["status"], "queued")


class RepoOverviewTests(unittest.TestCase):
    def test_build_repo_overview_collects_docs_commands_and_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / "artifacts" / "modelling").mkdir(parents=True)
            (repo_root / "artifacts" / "modelling" / "pipeline.md").write_text("# pipeline", encoding="utf-8")
            (repo_root / "artifacts" / "modelling" / "data_model.md").write_text("# data model", encoding="utf-8")
            (repo_root / "artifacts" / "modelling" / "decision_record_schema.md").write_text(
                "# decision record",
                encoding="utf-8",
            )
            (repo_root / "demo-show-brief.png").write_bytes(b"png")

            overview = build_repo_overview(repo_root=repo_root)

            diagram_cards = {card["id"]: card for card in overview["diagram_cards"]}
            self.assertEqual(sorted(diagram_cards), ["architecture", "data_model", "run_flow"])
            self.assertTrue(diagram_cards["architecture"]["primary_path"].endswith("pipeline.md"))
            self.assertEqual(diagram_cards["architecture"]["assets"][0]["kind"], "image")
            self.assertEqual(sorted(overview["commands"]), ["evals", "fixture", "live", "targeted_tests"])


class ArtifactReaderTests(unittest.TestCase):
    def test_discover_dashboard_artifacts_returns_latest_run_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            demo_base = repo_root / ".tmp_repo_dashboard" / "demo"
            live_base = repo_root / ".tmp_repo_dashboard" / "live"

            demo_brief = demo_base / "artifacts" / "daily" / "2026-03-15" / "brief.html"
            demo_brief.parent.mkdir(parents=True, exist_ok=True)
            demo_brief.write_text("<html>demo</html>", encoding="utf-8")

            demo_record = demo_base / "artifacts" / "decision_records" / "2026-03-15" / "run_daily_fixture.json"
            demo_record.parent.mkdir(parents=True, exist_ok=True)
            demo_record.write_text(
                json.dumps(
                    {
                        "publish_decision": "hold",
                        "reason_codes": ["source_scarcity_detected"],
                        "decision_rationale": {"summary": "Sparse evidence"},
                    }
                ),
                encoding="utf-8",
            )

            demo_summary = (
                demo_base
                / "artifacts"
                / "runtime"
                / "daily_brief_runs"
                / "2026-03-15"
                / "run_daily_fixture"
                / "run_summary.json"
            )
            demo_summary.parent.mkdir(parents=True, exist_ok=True)
            demo_summary.write_text(
                json.dumps(
                    {
                        "publish_decision": "hold",
                        "reason_codes": ["source_scarcity_detected"],
                        "guardrail_checks": {"notes": ["Sparse evidence"]},
                    }
                ),
                encoding="utf-8",
            )

            live_record = live_base / "artifacts" / "decision_records" / "2026-03-14" / "run_daily_live.json"
            live_record.parent.mkdir(parents=True, exist_ok=True)
            live_record.write_text(
                json.dumps(
                    {
                        "publish_decision": "publish",
                        "reason_codes": ["two_distinct_debates_supported"],
                        "decision_rationale": {"summary": "Healthy live run"},
                    }
                ),
                encoding="utf-8",
            )

            artifacts = discover_dashboard_artifacts(repo_root=repo_root)

            demo_entry = artifacts["by_kind"]["fixture"]
            self.assertTrue(demo_entry["brief_html_uri"].endswith("/brief.html"))
            self.assertEqual(demo_entry["publish_decision"], "hold")
            self.assertEqual(demo_entry["reason_codes"], ["source_scarcity_detected"])
            self.assertEqual(demo_entry["reason"], "Sparse evidence")

            latest = artifacts["latest"]
            self.assertEqual(latest["run_kind"], "fixture")
            self.assertEqual(latest["publish_decision"], "hold")
            self.assertTrue(latest["decision_record_uri"].endswith("/run_daily_fixture.json"))


if __name__ == "__main__":
    unittest.main()
