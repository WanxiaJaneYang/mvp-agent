from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.agent.pipeline.types import (
    SourceCollectionStatus,
    SourceContentMode,
    SourceFetchVia,
    SourceOnboardingRunStatus,
    SourceStrategyState,
    SourceStrategyStatus,
)
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
                    "strategy_state": SourceStrategyState.MISSING,
                    "current_strategy_id": None,
                    "latest_strategy_id": None,
                    "last_onboarding_run_id": None,
                    "last_collection_status": SourceCollectionStatus.IDLE,
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
                    "strategy_status": SourceStrategyStatus.PROPOSED,
                    "entrypoint_url": "https://www.reuters.com/business/",
                    "fetch_via": SourceFetchVia.DIRECT_RSS,
                    "content_mode": SourceContentMode.ARTICLE_FULL_TEXT,
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
                    "status": SourceOnboardingRunStatus.QUEUED,
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
            self.assertEqual(state["strategy_state"], SourceStrategyState.MISSING)
            self.assertEqual(strategies[0]["strategy_id"], "strat_001")
            self.assertEqual(runs[0]["onboarding_run_id"], "onboard_001")

            store.update_onboarding_run(
                "onboard_001",
                status=SourceOnboardingRunStatus.SUCCEEDED,
                proposed_strategy_id="strat_001",
                finished_at="2026-04-04T00:10:00Z",
                result_summary_json="{\"status\":\"ready_for_review\"}",
            )
            updated_runs = store.list_onboarding_runs("reuters_business")

            self.assertEqual(updated_runs[0]["status"], SourceOnboardingRunStatus.SUCCEEDED)
            self.assertEqual(updated_runs[0]["proposed_strategy_id"], "strat_001")

    def test_update_onboarding_run_preserves_nullable_fields_until_explicitly_cleared(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SourceControlPlaneStore(base_dir=Path(tmpdir))

            store.insert_onboarding_run(
                {
                    "onboarding_run_id": "onboard_001",
                    "source_id": "reuters_business",
                    "status": SourceOnboardingRunStatus.FAILED,
                    "worker_kind": "claude_code_headless",
                    "worker_ref": None,
                    "submitted_at": "2026-04-04T00:01:00Z",
                    "started_at": "2026-04-04T00:02:00Z",
                    "finished_at": "2026-04-04T00:03:00Z",
                    "proposed_strategy_id": None,
                    "error_message": "timeout",
                    "result_summary_json": "{\"status\":\"failed\"}",
                }
            )

            store.update_onboarding_run(
                "onboard_001",
                status=SourceOnboardingRunStatus.FAILED,
                error_message=None,
                result_summary_json=None,
            )
            preserved_run = store.list_onboarding_runs("reuters_business")[0]

            self.assertEqual(preserved_run["error_message"], "timeout")
            self.assertEqual(preserved_run["result_summary_json"], "{\"status\":\"failed\"}")

            store.update_onboarding_run(
                "onboard_001",
                status=SourceOnboardingRunStatus.FAILED,
                clear_error_message=True,
                clear_result_summary_json=True,
            )
            cleared_run = store.list_onboarding_runs("reuters_business")[0]

            self.assertIsNone(cleared_run["error_message"])
            self.assertIsNone(cleared_run["result_summary_json"])

    def test_upsert_operator_state_overwrites_existing_row(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SourceControlPlaneStore(base_dir=Path(tmpdir))

            store.upsert_operator_state(
                {
                    "source_id": "reuters_business",
                    "is_active": 1,
                    "strategy_state": SourceStrategyState.MISSING,
                    "current_strategy_id": None,
                    "latest_strategy_id": None,
                    "last_onboarding_run_id": None,
                    "last_collection_status": SourceCollectionStatus.IDLE,
                    "last_collection_started_at": None,
                    "last_collection_finished_at": None,
                    "last_collection_error": None,
                    "activated_at": "2026-04-04T00:00:00Z",
                    "deactivated_at": None,
                    "updated_at": "2026-04-04T00:00:00Z",
                }
            )
            store.upsert_operator_state(
                {
                    "source_id": "reuters_business",
                    "is_active": 1,
                    "strategy_state": SourceStrategyState.READY,
                    "current_strategy_id": "strat_001",
                    "latest_strategy_id": "strat_001",
                    "last_onboarding_run_id": "onboard_001",
                    "last_collection_status": SourceCollectionStatus.SUCCEEDED,
                    "last_collection_started_at": "2026-04-04T00:01:00Z",
                    "last_collection_finished_at": "2026-04-04T00:02:00Z",
                    "last_collection_error": None,
                    "activated_at": "2026-04-04T00:00:00Z",
                    "deactivated_at": None,
                    "updated_at": "2026-04-04T00:02:00Z",
                }
            )

            state = store.get_operator_state("reuters_business")

            self.assertIsNotNone(state)
            self.assertEqual(state["strategy_state"], SourceStrategyState.READY)
            self.assertEqual(state["current_strategy_id"], "strat_001")
            self.assertEqual(state["last_collection_status"], SourceCollectionStatus.SUCCEEDED)

    def test_list_strategy_versions_by_source_ids_groups_multiple_sources(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SourceControlPlaneStore(base_dir=Path(tmpdir))

            store.insert_strategy_version(
                {
                    "strategy_id": "strat_reuters_001",
                    "source_id": "reuters_business",
                    "version": 1,
                    "strategy_status": SourceStrategyStatus.PROPOSED,
                    "entrypoint_url": "https://www.reuters.com/business/",
                    "fetch_via": SourceFetchVia.DIRECT_RSS,
                    "content_mode": SourceContentMode.ARTICLE_FULL_TEXT,
                    "parser_profile": None,
                    "max_items_per_run": 25,
                    "strategy_summary_json": "{}",
                    "strategy_details_json": "{}",
                    "created_from_run_id": None,
                    "created_at": "2026-04-04T00:05:00Z",
                    "approved_at": None,
                }
            )
            store.insert_strategy_version(
                {
                    "strategy_id": "strat_bls_001",
                    "source_id": "us_bls_news",
                    "version": 1,
                    "strategy_status": SourceStrategyStatus.PROPOSED,
                    "entrypoint_url": "https://www.bls.gov/feed/bls_latest.rss",
                    "fetch_via": SourceFetchVia.DIRECT_RSS,
                    "content_mode": SourceContentMode.FEED_INDEX,
                    "parser_profile": None,
                    "max_items_per_run": 20,
                    "strategy_summary_json": "{}",
                    "strategy_details_json": "{}",
                    "created_from_run_id": None,
                    "created_at": "2026-04-04T00:06:00Z",
                    "approved_at": None,
                }
            )

            grouped = store.list_strategy_versions_by_source_ids(
                ["reuters_business", "us_bls_news", "missing_source"]
            )

            self.assertEqual([item["strategy_id"] for item in grouped["reuters_business"]], ["strat_reuters_001"])
            self.assertEqual([item["strategy_id"] for item in grouped["us_bls_news"]], ["strat_bls_001"])
            self.assertEqual(grouped["missing_source"], [])

    def test_rejects_invalid_lifecycle_status_values(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = SourceControlPlaneStore(base_dir=Path(tmpdir))

            with self.assertRaises(sqlite3.IntegrityError):
                store.upsert_operator_state(
                    {
                        "source_id": "reuters_business",
                        "is_active": 1,
                        "strategy_state": "weird",  # type: ignore[typeddict-item]
                        "current_strategy_id": None,
                        "latest_strategy_id": None,
                        "last_onboarding_run_id": None,
                        "last_collection_status": SourceCollectionStatus.IDLE,
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
                        "strategy_status": "live_now",  # type: ignore[typeddict-item]
                        "entrypoint_url": "https://www.reuters.com/business/",
                        "fetch_via": SourceFetchVia.DIRECT_RSS,
                        "content_mode": SourceContentMode.ARTICLE_FULL_TEXT,
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
                        "status": "stuck",  # type: ignore[typeddict-item]
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
