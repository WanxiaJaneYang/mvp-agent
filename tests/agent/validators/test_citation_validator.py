import unittest

from apps.agent.validators.citation_validator import validate_synthesis


class CitationValidatorTests(unittest.TestCase):
    def test_valid_core_sections_pass_without_removals(self):
        synthesis = {
            "prevailing": [{"text": "Fed held rates.", "citation_ids": ["c1"]}],
            "counter": [{"text": "Growth could slow.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Disinflation may accelerate.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch payroll revisions.", "citation_ids": ["c4"]}],
        }
        store = {
            "c1": {"id": "c1", "url": "u1", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c4": {"id": "c4", "url": "u4", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
        }

        report = validate_synthesis(synthesis, store)

        self.assertTrue(report.validation_passed)
        self.assertEqual(report.removed_bullets, 0)
        self.assertFalse(report.should_retry)

    def test_missing_citations_replaced_with_insufficient_evidence(self):
        synthesis = {
            "prevailing": [{"text": "Uncited claim.", "citation_ids": []}],
            "counter": [{"text": "Cited counter.", "citation_ids": ["c1"]}],
            "minority": [{"text": "Cited minority.", "citation_ids": ["c2"]}],
            "watch": [{"text": "Cited watch.", "citation_ids": ["c3"]}],
        }
        store = {
            "c1": {"id": "c1", "url": "u1", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
        }

        report = validate_synthesis(synthesis, store)

        self.assertEqual(report.removed_bullets, 1)
        self.assertIn("Insufficient evidence", report.synthesis["prevailing"][0]["text"])
        self.assertEqual(report.total_bullets, 4)
        self.assertEqual(report.cited_bullets, 3)

    def test_invalid_citation_fields_are_removed(self):
        synthesis = {
            "prevailing": [{"text": "Claim.", "citation_ids": ["c_missing"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c1"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c2"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c3"]}],
        }
        store = {
            "c_missing": {"id": "c_missing", "url": "", "published_at": None, "paywall_policy": "full"},
            "c1": {"id": "c1", "url": "u1", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
        }

        report = validate_synthesis(synthesis, store)

        self.assertEqual(report.removed_bullets, 1)
        self.assertEqual(report.synthesis["prevailing"][0]["citation_ids"], [])
        self.assertIn("Insufficient evidence", report.synthesis["prevailing"][0]["text"])

    def test_paywalled_quote_span_is_stripped(self):
        synthesis = {
            "prevailing": [{"text": "Claim.", "citation_ids": ["c1"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
        }
        store = {
            "c1": {
                "id": "c1",
                "url": "u1",
                "published_at": "2026-02-19T00:00:00Z",
                "paywall_policy": "metadata_only",
                "quote_span": {"text": "secret"},
                "snippet_span": {"text": "headline"},
            },
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c4": {"id": "c4", "url": "u4", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
        }

        report = validate_synthesis(synthesis, store)

        self.assertNotIn("quote_span", report.citation_store["c1"])
        self.assertIn("snippet_span", report.citation_store["c1"])

    def test_section_empty_triggers_retry(self):
        synthesis = {
            "prevailing": [{"text": "Bad.", "citation_ids": []}],
            "counter": [{"text": "Counter.", "citation_ids": ["c1"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c2"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c3"]}],
        }
        store = {
            "c1": {"id": "c1", "url": "u1", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
        }

        report = validate_synthesis(synthesis, store, replace_with_placeholder=False)

        self.assertTrue(report.should_retry)
        self.assertFalse(report.validation_passed)

    def test_non_core_sections_pass_through_unchanged(self):
        synthesis = {
            "prevailing": [{"text": "Fed held rates.", "citation_ids": ["c1"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
            "other": [{"text": "Analyst note", "extra_field": "x"}],
            "metadata": {"author": "Analyst", "version": 1},
        }
        store = {
            "c1": {"id": "c1", "url": "u1", "published_at": "2026-02-19T00:00:00Z"},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z"},
            "c4": {"id": "c4", "url": "u4", "published_at": "2026-02-19T00:00:00Z"},
        }
        report = validate_synthesis(synthesis, store)
        self.assertEqual(report.synthesis["other"], synthesis["other"])
        self.assertEqual(report.synthesis["metadata"], synthesis["metadata"])

    def test_retry_triggered_when_removed_bullets_exceed_threshold(self):
        synthesis = {
            "prevailing": [
                {"text": "Bad 1.", "citation_ids": []},
                {"text": "Bad 2.", "citation_ids": []},
                {"text": "Bad 3.", "citation_ids": []},
                {"text": "Bad 4.", "citation_ids": []},
            ],
            "counter": [{"text": "Counter.", "citation_ids": ["c1"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c2"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c3"]}],
        }
        store = {
            "c1": {"id": "c1", "url": "u1", "published_at": "2026-02-19T00:00:00Z"},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z"},
        }
        report = validate_synthesis(
            synthesis, store, replace_with_placeholder=False, max_removed_without_retry=3
        )
        self.assertTrue(report.should_retry)
        self.assertFalse(report.validation_passed)

    def test_citation_ids_not_list_becomes_uncited_and_removed(self):
        synthesis = {
            "prevailing": [{"text": "Claim.", "citation_ids": "c1"}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
        }
        store = {
            "c1": {"id": "c1", "url": "u1", "published_at": "2026-02-19T00:00:00Z"},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z"},
            "c4": {"id": "c4", "url": "u4", "published_at": "2026-02-19T00:00:00Z"},
        }
        report = validate_synthesis(synthesis, store)
        self.assertEqual(report.removed_bullets, 1)

    def test_non_dict_bullet_is_normalized_and_removed_when_uncited(self):
        synthesis = {
            "prevailing": ["not a dict bullet"],
            "counter": [{"text": "Counter.", "citation_ids": ["c1"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c2"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c3"]}],
        }
        store = {
            "c1": {"id": "c1", "url": "u1", "published_at": "2026-02-19T00:00:00Z"},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z"},
        }
        report = validate_synthesis(synthesis, store)
        self.assertEqual(report.removed_bullets, 1)

    def test_mixed_valid_and_invalid_citations_keeps_valid_ones(self):
        synthesis = {
            "prevailing": [{"text": "Claim.", "citation_ids": ["c_valid", "c_missing"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
        }
        store = {
            "c_valid": {"id": "c_valid", "url": "u1", "published_at": "2026-02-19T00:00:00Z"},
            "c_missing": {"id": "c_missing", "url": "", "published_at": None},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z"},
            "c4": {"id": "c4", "url": "u4", "published_at": "2026-02-19T00:00:00Z"},
        }
        report = validate_synthesis(synthesis, store)
        self.assertEqual(report.removed_bullets, 0)
        self.assertEqual(report.synthesis["prevailing"][0]["citation_ids"], ["c_valid"])

    def test_multisentence_bullet_allows_shared_citation_ids_without_span_mapping(self):
        synthesis = {
            "prevailing": [{"text": "Claim one. Claim two.", "citation_ids": ["c1"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
        }
        store = {
            "c1": {"id": "c1", "url": "https://source1.example/doc", "published_at": "2026-02-19T00:00:00Z"},
            "c2": {"id": "c2", "url": "https://source2.example/doc", "published_at": "2026-02-19T00:00:00Z"},
            "c3": {"id": "c3", "url": "https://source3.example/doc", "published_at": "2026-02-19T00:00:00Z"},
            "c4": {"id": "c4", "url": "https://source4.example/doc", "published_at": "2026-02-19T00:00:00Z"},
        }

        report = validate_synthesis(synthesis, store)

        self.assertEqual(report.removed_bullets, 0)
        self.assertEqual(report.synthesis["prevailing"][0]["citation_ids"], ["c1"])

    def test_missing_citation_id_in_store_is_removed(self):
        synthesis = {
            "prevailing": [{"text": "Claim.", "citation_ids": ["c_missing"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
        }
        store = {
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z"},
            "c4": {"id": "c4", "url": "u4", "published_at": "2026-02-19T00:00:00Z"},
        }

        report = validate_synthesis(synthesis, store)

        self.assertEqual(report.removed_bullets, 1)
        self.assertIn("Insufficient evidence", report.synthesis["prevailing"][0]["text"])

    def test_placeholder_only_core_section_triggers_retry(self):
        synthesis = {
            "prevailing": [{"text": "Bad.", "citation_ids": []}],
            "counter": [{"text": "Counter.", "citation_ids": ["c1"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c2"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c3"]}],
        }
        store = {
            "c1": {"id": "c1", "url": "u1", "published_at": "2026-02-19T00:00:00Z"},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z"},
        }

        report = validate_synthesis(synthesis, store, replace_with_placeholder=True)

        self.assertTrue(report.should_retry)
        self.assertIn("prevailing", report.empty_core_sections)
        self.assertEqual(report.synthesis["prevailing"][0]["text"], "[Insufficient evidence to support this claim]")

    def test_source_registry_missing_source_id_skips_registry_matching(self):
        synthesis = {
            "prevailing": [{"text": "Claim.", "citation_ids": ["c1"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
        }
        store = {
            "c1": {
                "id": "c1",
                "url": "https://federalreserve.gov/newsevents/some-path",
                "published_at": "2026-02-19T00:00:00Z",
            },
            "c2": {"id": "c2", "url": "https://source2.example/doc", "published_at": "2026-02-19T00:00:00Z"},
            "c3": {"id": "c3", "url": "https://source3.example/doc", "published_at": "2026-02-19T00:00:00Z"},
            "c4": {"id": "c4", "url": "https://source4.example/doc", "published_at": "2026-02-19T00:00:00Z"},
        }
        source_registry = {
            "fed": {"base_url": "https://federalreserve.gov/newsevents"},
            "src2": {"base_url": "https://source2.example"},
            "src3": {"base_url": "https://source3.example"},
            "src4": {"base_url": "https://source4.example"},
        }

        report = validate_synthesis(synthesis, store, source_registry=source_registry)

        self.assertEqual(report.removed_bullets, 0)

    def test_source_registry_url_mismatch_invalidates_citation(self):
        synthesis = {
            "prevailing": [{"text": "Claim.", "citation_ids": ["c1"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
        }
        store = {
            "c1": {
                "id": "c1",
                "url": "https://wrong.example/doc",
                "published_at": "2026-02-19T00:00:00Z",
                "source_id": "fed",
            },
            "c2": {
                "id": "c2",
                "url": "https://source2.example/doc",
                "published_at": "2026-02-19T00:00:00Z",
                "source_id": "src2",
            },
            "c3": {
                "id": "c3",
                "url": "https://source3.example/doc",
                "published_at": "2026-02-19T00:00:00Z",
                "source_id": "src3",
            },
            "c4": {
                "id": "c4",
                "url": "https://source4.example/doc",
                "published_at": "2026-02-19T00:00:00Z",
                "source_id": "src4",
            },
        }
        source_registry = {
            "fed": {"base_url": "https://federalreserve.gov/newsevents"},
            "src2": {"base_url": "https://source2.example"},
            "src3": {"base_url": "https://source3.example"},
            "src4": {"base_url": "https://source4.example"},
        }

        report = validate_synthesis(synthesis, store, source_registry=source_registry)

        self.assertEqual(report.removed_bullets, 1)
        self.assertEqual(report.synthesis["prevailing"][0]["citation_ids"], [])


if __name__ == "__main__":
    unittest.main()
