from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from apps.agent.runtime.resolved_sources import load_resolved_sources
from apps.agent.storage.source_control_plane import SourceControlPlaneStore


class ResolvedSourcesTests(unittest.TestCase):
    def test_marks_only_active_ready_sources_as_runtime_eligible(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            registry_path = base_dir / "registry.yaml"
            registry_path.write_text(
                yaml.safe_dump(
                    {
                        "sources": [
                            {
                                "id": "reuters_business",
                                "name": "Reuters - Business News",
                                "url": "https://www.reuters.com/business/",
                                "type": "rss",
                                "credibility_tier": 2,
                                "paywall_policy": "full",
                                "fetch_interval": "daily",
                                "tags": ["market_narrative", "us"],
                            },
                            {
                                "id": "wsj_markets",
                                "name": "Wall Street Journal - Markets",
                                "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
                                "type": "rss",
                                "credibility_tier": 2,
                                "paywall_policy": "metadata_only",
                                "fetch_interval": "daily",
                                "tags": ["market_narrative", "us"],
                            },
                        ]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            store = SourceControlPlaneStore(base_dir=base_dir)
            store.upsert_operator_state(
                {
                    "source_id": "reuters_business",
                    "is_active": 1,
                    "strategy_state": "ready",
                    "current_strategy_id": "strat_reuters_001",
                    "latest_strategy_id": "strat_reuters_001",
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
                    "strategy_id": "strat_reuters_001",
                    "source_id": "reuters_business",
                    "version": 1,
                    "strategy_status": "approved",
                    "entrypoint_url": "https://www.reuters.com/business/",
                    "fetch_via": "direct_rss",
                    "content_mode": "article_full_text",
                    "parser_profile": None,
                    "max_items_per_run": 25,
                    "strategy_summary_json": "{\"headline\":\"business feed\"}",
                    "strategy_details_json": "{\"entrypoints\":[\"https://www.reuters.com/business/\"]}",
                    "created_from_run_id": None,
                    "created_at": "2026-04-04T00:05:00Z",
                    "approved_at": "2026-04-04T00:06:00Z",
                }
            )
            store.upsert_operator_state(
                {
                    "source_id": "wsj_markets",
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

            resolved = load_resolved_sources(base_dir=base_dir, registry_path=registry_path)
            eligible = [item for item in resolved if item["runtime_eligible"]]

            self.assertEqual([item["source_id"] for item in eligible], ["reuters_business"])
            self.assertEqual(eligible[0]["current_strategy"]["strategy_id"], "strat_reuters_001")


if __name__ == "__main__":
    unittest.main()
