import tempfile
import unittest
from pathlib import Path

import yaml

from apps.agent.pipeline.types import SourceContentMode, SourceFetchVia, SourceRole
from apps.agent.runtime.source_scope import load_active_source_subset, load_source_registry


class SourceScopeTests(unittest.TestCase):
    def test_load_active_source_subset_resolves_expected_ids_in_order(self):
        subset = load_active_source_subset()

        self.assertEqual(
            [source["id"] for source in subset],
            [
                "fed_press_releases",
                "us_bls_news",
                "us_bea_news",
                "reuters_business",
                "wsj_markets",
                "jpmorgan_am_research",
            ],
        )

    def test_subset_contains_required_source_mix(self):
        subset = load_active_source_subset()

        tier_1_count = sum(1 for source in subset if source["credibility_tier"] == 1)
        metadata_only_count = sum(
            1 for source in subset if source["paywall_policy"] == "metadata_only"
        )

        self.assertGreaterEqual(tier_1_count, 3)
        self.assertEqual(metadata_only_count, 1)
        self.assertIn("Reuters - Business News", {source["name"] for source in subset})
        self.assertTrue(
            any("institutional_letter" in source.get("tags", []) for source in subset)
        )

    def test_missing_source_id_in_allowlist_raises_value_error(self):
        registry = load_source_registry()

        with tempfile.TemporaryDirectory() as temp_dir:
            active_ids_path = Path(temp_dir) / "active_sources.yaml"
            active_ids_path.write_text(
                yaml.safe_dump(
                    {"active_source_ids": ["fed_press_releases", "missing_source"]}, sort_keys=False
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_active_source_subset(registry=registry, active_ids_path=active_ids_path)

    def test_load_source_registry_normalizes_optional_contract_enums(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "source_registry.yaml"
            registry_path.write_text(
                yaml.safe_dump(
                    {
                        "sources": [
                            {
                                "id": "reuters_business",
                                "name": "Reuters - Business News",
                                "url": "https://www.reuters.com/business/",
                                "type": "rss",
                                "credibility_tier": 1,
                                "paywall_policy": "full",
                                "fetch_interval": "daily",
                                "fetch_via": "direct_rss",
                                "source_role": "supplementary",
                                "timestamp_authority": "feed_timestamp",
                                "content_mode": "feed_index",
                            }
                        ]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            registry = load_source_registry(registry_path=registry_path)

            self.assertEqual(registry["reuters_business"]["fetch_via"], SourceFetchVia.DIRECT_RSS)
            self.assertEqual(registry["reuters_business"]["source_role"], SourceRole.SUPPLEMENTARY)
            self.assertEqual(
                registry["reuters_business"]["content_mode"], SourceContentMode.FEED_INDEX
            )

    def test_invalid_source_contract_enum_value_includes_source_id_and_field_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "source_registry.yaml"
            registry_path.write_text(
                yaml.safe_dump(
                    {
                        "sources": [
                            {
                                "id": "reuters_business",
                                "name": "Reuters - Business News",
                                "url": "https://www.reuters.com/business/",
                                "type": "rss",
                                "credibility_tier": 1,
                                "paywall_policy": "full",
                                "fetch_interval": "daily",
                                "fetch_via": "scrape",
                            }
                        ]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                r"Invalid 'fetch_via' value 'scrape' for source 'reuters_business'",
            ):
                load_source_registry(registry_path=registry_path)

    def test_validate_artifacts_script_includes_runtime_subset_artifact(self):
        validate_script = (
            Path(__file__).resolve().parents[3] / "scripts" / "validate_artifacts.py"
        ).read_text(encoding="utf-8")

        self.assertIn("artifacts/runtime/v1_active_sources.yaml", validate_script)

    def test_readme_documents_v1_active_subset_first(self):
        readme_text = (Path(__file__).resolve().parents[3] / "README.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("active source subset", readme_text)
        self.assertIn("fed_press_releases", readme_text)


if __name__ == "__main__":
    unittest.main()
