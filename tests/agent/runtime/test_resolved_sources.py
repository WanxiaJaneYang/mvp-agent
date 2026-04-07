from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from apps.agent.pipeline.types import (
    SourceCollectionStatus,
    SourceContentMode,
    SourceFetchVia,
    SourceRole,
    SourceStrategyState,
    SourceStrategyStatus,
    SourceTimestampAuthority,
)
from apps.agent.runtime.resolved_sources import get_resolved_source, load_resolved_sources
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
                    "strategy_state": SourceStrategyState.READY,
                    "current_strategy_id": "strat_reuters_001",
                    "latest_strategy_id": "strat_reuters_001",
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
                    "strategy_id": "strat_reuters_001",
                    "source_id": "reuters_business",
                    "version": 1,
                    "strategy_status": SourceStrategyStatus.APPROVED,
                    "entrypoint_url": "https://www.reuters.com/business/",
                    "fetch_via": SourceFetchVia.DIRECT_RSS,
                    "content_mode": SourceContentMode.ARTICLE_FULL_TEXT,
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

            resolved = load_resolved_sources(base_dir=base_dir, registry_path=registry_path)
            eligible = [item for item in resolved if item["runtime_eligible"]]

            self.assertEqual([item["source_id"] for item in eligible], ["reuters_business"])
            self.assertEqual(eligible[0]["current_strategy"]["strategy_id"], "strat_reuters_001")

    def test_fallback_contract_semantics_remain_conservative_for_unannotated_sources(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            registry_path = base_dir / "registry.yaml"
            registry_path.write_text(
                yaml.safe_dump(
                    {
                        "sources": [
                            {
                                "id": "zerohedge",
                                "name": "Zero Hedge - Markets",
                                "url": "https://www.zerohedge.com/s/RSS",
                                "type": "rss",
                                "credibility_tier": 4,
                                "paywall_policy": "full",
                                "fetch_interval": "daily",
                                "tags": ["market_narrative", "contrarian"],
                            },
                            {
                                "id": "us_bls_schedule",
                                "name": "U.S. Bureau of Labor Statistics - Economic Release Schedule",
                                "url": "https://www.bls.gov/schedule/news_release/",
                                "type": "html",
                                "credibility_tier": 1,
                                "paywall_policy": "full",
                                "fetch_interval": "weekly",
                                "tags": ["macro_data", "event_calendar", "us"],
                            },
                            {
                                "id": "seekingalpha_news",
                                "name": "Seeking Alpha - Market News",
                                "url": "https://seekingalpha.com/market-news",
                                "type": "html",
                                "credibility_tier": 4,
                                "paywall_policy": "metadata_only",
                                "fetch_interval": "daily",
                                "tags": ["market_narrative", "equity_risk"],
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

            resolved = {
                item["source_id"]: item
                for item in load_resolved_sources(base_dir=base_dir, registry_path=registry_path)
            }

            self.assertEqual(resolved["zerohedge"]["contract"]["source_role"], SourceRole.MONITOR_ONLY)
            self.assertEqual(resolved["zerohedge"]["contract"]["fetch_via"], SourceFetchVia.DIRECT_RSS)
            self.assertEqual(
                resolved["zerohedge"]["contract"]["timestamp_authority"],
                SourceTimestampAuthority.FEED_TIMESTAMP,
            )
            self.assertEqual(
                resolved["zerohedge"]["contract"]["content_mode"],
                SourceContentMode.FEED_INDEX,
            )

            self.assertEqual(
                resolved["us_bls_schedule"]["contract"]["source_role"],
                SourceRole.SUPPLEMENTARY,
            )
            self.assertEqual(
                resolved["us_bls_schedule"]["contract"]["fetch_via"],
                SourceFetchVia.DIRECT_HTML,
            )
            self.assertEqual(
                resolved["us_bls_schedule"]["contract"]["timestamp_authority"],
                SourceTimestampAuthority.RETRIEVAL_TIME_ONLY,
            )
            self.assertEqual(
                resolved["us_bls_schedule"]["contract"]["content_mode"],
                SourceContentMode.CALENDAR_EVENT,
            )

            self.assertEqual(
                resolved["seekingalpha_news"]["contract"]["source_role"],
                SourceRole.MONITOR_ONLY,
            )
            self.assertEqual(
                resolved["seekingalpha_news"]["contract"]["fetch_via"],
                SourceFetchVia.DIRECT_HTML,
            )
            self.assertEqual(
                resolved["seekingalpha_news"]["contract"]["timestamp_authority"],
                SourceTimestampAuthority.RETRIEVAL_TIME_ONLY,
            )
            self.assertEqual(
                resolved["seekingalpha_news"]["contract"]["content_mode"],
                SourceContentMode.SNIPPET_ONLY,
            )

            self.assertEqual(
                resolved["wsj_markets"]["contract"]["source_role"],
                SourceRole.SUPPLEMENTARY,
            )
            self.assertEqual(
                resolved["wsj_markets"]["contract"]["fetch_via"],
                SourceFetchVia.DIRECT_RSS,
            )
            self.assertEqual(
                resolved["wsj_markets"]["contract"]["timestamp_authority"],
                SourceTimestampAuthority.FEED_TIMESTAMP,
            )
            self.assertEqual(
                resolved["wsj_markets"]["contract"]["content_mode"],
                SourceContentMode.SNIPPET_ONLY,
            )

    def test_get_resolved_source_returns_none_for_missing_current_strategy_pointer(self) -> None:
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
                            }
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
                    "strategy_state": SourceStrategyState.READY,
                    "current_strategy_id": "strat_missing",
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

            resolved = get_resolved_source(
                "reuters_business",
                base_dir=base_dir,
                registry_path=registry_path,
            )

            self.assertIsNone(resolved["current_strategy"])
            self.assertFalse(resolved["runtime_eligible"])


if __name__ == "__main__":
    unittest.main()
