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


if __name__ == "__main__":
    unittest.main()
