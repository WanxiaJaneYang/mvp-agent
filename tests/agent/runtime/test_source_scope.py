from pathlib import Path
import tempfile
import unittest

import yaml

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
            ],
        )

    def test_subset_contains_required_source_mix(self):
        subset = load_active_source_subset()

        tier_1_count = sum(1 for source in subset if source["credibility_tier"] == 1)
        metadata_only_count = sum(1 for source in subset if source["paywall_policy"] == "metadata_only")

        self.assertGreaterEqual(tier_1_count, 3)
        self.assertEqual(metadata_only_count, 1)
        self.assertIn("Reuters - Business News", {source["name"] for source in subset})

    def test_missing_source_id_in_allowlist_raises_value_error(self):
        registry = load_source_registry()

        with tempfile.TemporaryDirectory() as temp_dir:
            active_ids_path = Path(temp_dir) / "active_sources.yaml"
            active_ids_path.write_text(
                yaml.safe_dump({"active_source_ids": ["fed_press_releases", "missing_source"]}, sort_keys=False),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_active_source_subset(registry=registry, active_ids_path=active_ids_path)

    def test_validate_artifacts_script_includes_runtime_subset_artifact(self):
        validate_script = (Path(__file__).resolve().parents[3] / "scripts" / "validate_artifacts.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("artifacts/runtime/v1_active_sources.yaml", validate_script)

    def test_readme_documents_v1_active_subset_first(self):
        readme_text = (Path(__file__).resolve().parents[3] / "README.md").read_text(encoding="utf-8")

        self.assertIn("active source subset", readme_text)
        self.assertIn("fed_press_releases", readme_text)


if __name__ == "__main__":
    unittest.main()
