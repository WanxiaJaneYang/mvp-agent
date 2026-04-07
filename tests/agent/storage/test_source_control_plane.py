from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.agent.storage.source_control_plane import (
    SourceControlPlaneStore,
    control_plane_db_path,
    ensure_control_plane_db,
)


class SourceControlPlaneStoreTests(unittest.TestCase):
    def test_bootstraps_control_plane_tables(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            db_path = ensure_control_plane_db(base_dir=base_dir)

            self.assertEqual(db_path, control_plane_db_path(base_dir=base_dir))
            self.assertTrue(db_path.exists())

            store = SourceControlPlaneStore(base_dir=base_dir)
            operator_state = store.get_operator_state("reuters_business")

            self.assertIsNone(operator_state)

    def test_persists_operator_state_strategy_versions_and_onboarding_runs(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SourceControlPlaneStore(base_dir=Path(tmpdir))

            store.upsert_operator_state(
                {
                    "source_id": "reuters_business",
                    "is_active": 1,
                    "strategy_state": "missing",
                    "current_strategy_id": None,
                    "latest_strategy_id": None,
                    "last_onboarding_run_id": None,
                    "last_collection_status": "idle",
                    "last_collection_started_at": None,
                    "last_collection_finished_at": None,
                    "last_collection_error": None,
                    "activated_at": "2026-04-04T00:00:00Z",
                    "deactivated_at": None,
                    "updated_at": "2026-04-04T00:00:00Z",
                }
            )
            store.insert_strategy_version(
                {
                    "strategy_id": "strat_001",
                    "source_id": "reuters_business",
                    "version": 1,
                    "strategy_status": "proposed",
                    "entrypoint_url": "https://www.reuters.com/business/",
                    "fetch_via": "direct_rss",
                    "content_mode": "article_full_text",
                    "parser_profile": None,
                    "max_items_per_run": 25,
                    "strategy_summary_json": "{\"headline\":\"business feed\"}",
                    "strategy_details_json": "{\"entrypoints\":[\"https://www.reuters.com/business/\"]}",
                    "created_from_run_id": None,
                    "created_at": "2026-04-04T00:05:00Z",
                    "approved_at": None,
                }
            )
            store.insert_onboarding_run(
                {
                    "onboarding_run_id": "onboard_001",
                    "source_id": "reuters_business",
                    "status": "queued",
                    "worker_kind": "claude_code_headless",
                    "worker_ref": None,
                    "submitted_at": "2026-04-04T00:01:00Z",
                    "started_at": None,
                    "finished_at": None,
                    "proposed_strategy_id": None,
                    "error_message": None,
                    "result_summary_json": None,
                }
            )

            state = store.get_operator_state("reuters_business")
            strategies = store.list_strategy_versions("reuters_business")
            runs = store.list_onboarding_runs("reuters_business")

            self.assertIsNotNone(state)
            self.assertEqual(state["strategy_state"], "missing")
            self.assertEqual(strategies[0]["strategy_id"], "strat_001")
            self.assertEqual(runs[0]["onboarding_run_id"], "onboard_001")

    def test_rejects_invalid_lifecycle_status_values(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SourceControlPlaneStore(base_dir=Path(tmpdir))

            with self.assertRaises(sqlite3.IntegrityError):
                store.upsert_operator_state(
                    {
                        "source_id": "reuters_business",
                        "is_active": 1,
                        "strategy_state": "weird",
                        "current_strategy_id": None,
                        "latest_strategy_id": None,
                        "last_onboarding_run_id": None,
                        "last_collection_status": "idle",
                        "last_collection_started_at": None,
                        "last_collection_finished_at": None,
                        "last_collection_error": None,
                        "activated_at": "2026-04-04T00:00:00Z",
                        "deactivated_at": None,
                        "updated_at": "2026-04-04T00:00:00Z",
                    }
                )

            with self.assertRaises(sqlite3.IntegrityError):
                store.insert_strategy_version(
                    {
                        "strategy_id": "strat_bad_001",
                        "source_id": "reuters_business",
                        "version": 1,
                        "strategy_status": "live_now",
                        "entrypoint_url": "https://www.reuters.com/business/",
                        "fetch_via": "direct_rss",
                        "content_mode": "article_full_text",
                        "parser_profile": None,
                        "max_items_per_run": 25,
                        "strategy_summary_json": "{}",
                        "strategy_details_json": "{}",
                        "created_from_run_id": None,
                        "created_at": "2026-04-04T00:05:00Z",
                        "approved_at": None,
                    }
                )

            with self.assertRaises(sqlite3.IntegrityError):
                store.insert_onboarding_run(
                    {
                        "onboarding_run_id": "onboard_bad_001",
                        "source_id": "reuters_business",
                        "status": "stuck",
                        "worker_kind": "claude_code_headless",
                        "worker_ref": None,
                        "submitted_at": "2026-04-04T00:01:00Z",
                        "started_at": None,
                        "finished_at": None,
                        "proposed_strategy_id": None,
                        "error_message": None,
                        "result_summary_json": None,
                    }
                )


if __name__ == "__main__":
    unittest.main()
