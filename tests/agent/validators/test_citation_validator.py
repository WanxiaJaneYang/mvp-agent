import unittest

from apps.agent.validators.citation_validator import validate_synthesis


class CitationValidatorTests(unittest.TestCase):
    def _citation(
        self,
        citation_id: str,
        *,
        url: str,
        published_at: str = "2026-02-19T00:00:00Z",
        paywall_policy: str = "full",
        source_id: str | None = None,
        publisher: str | None = None,
        quote_text: str | None = None,
        snippet_text: str | None = None,
    ) -> dict[str, object]:
        citation: dict[str, object] = {
            "citation_id": citation_id,
            "url": url,
            "published_at": published_at,
            "paywall_policy": paywall_policy,
        }
        if source_id is not None:
            citation["source_id"] = source_id
        if publisher is not None:
            citation["publisher"] = publisher
        if quote_text is not None:
            citation["quote_text"] = quote_text
        if snippet_text is not None:
            citation["snippet_text"] = snippet_text
        return citation

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

    def test_legacy_span_fields_are_normalized_to_runtime_fields(self):
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
        self.assertNotIn("snippet_span", report.citation_store["c1"])
        self.assertIsNone(report.citation_store["c1"]["quote_text"])
        self.assertEqual(report.citation_store["c1"]["snippet_text"], "headline")

    def test_metadata_only_citation_clears_quote_text_but_keeps_snippet_text(self):
        synthesis = {
            "prevailing": [{"text": "Claim.", "citation_ids": ["c1"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
        }
        store = {
            "c1": self._citation(
                "c1",
                url="https://example.test/metadata-only",
                paywall_policy="metadata_only",
                source_id="wsj_markets",
                publisher="Wall Street Journal",
                quote_text="fabricated quote",
                snippet_text="Headline only.",
            ),
            "c2": self._citation("c2", url="https://source2.example/doc"),
            "c3": self._citation("c3", url="https://source3.example/doc"),
            "c4": self._citation("c4", url="https://source4.example/doc"),
        }

        report = validate_synthesis(synthesis, store)

        self.assertIsNone(report.citation_store["c1"]["quote_text"])
        self.assertEqual(report.citation_store["c1"]["snippet_text"], "Headline only.")

    def test_numeric_claim_requires_credible_or_independent_citations_when_registry_available(self):
        synthesis = {
            "prevailing": [{"text": "Markets fell 2% yesterday.", "citation_ids": ["c1"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
        }
        store = {
            "c1": self._citation(
                "c1",
                url="https://tier3.example/markets",
                source_id="tier3_markets",
                publisher="Tier 3 Markets",
            ),
            "c2": self._citation("c2", url="https://source2.example/doc"),
            "c3": self._citation("c3", url="https://source3.example/doc"),
            "c4": self._citation("c4", url="https://source4.example/doc"),
        }
        source_registry = {
            "tier3_markets": {
                "base_url": "https://tier3.example",
                "credibility_tier": 3,
                "tags": ["market_narrative"],
            },
            "src2": {"base_url": "https://source2.example", "credibility_tier": 2, "tags": ["market_narrative"]},
            "src3": {"base_url": "https://source3.example", "credibility_tier": 2, "tags": ["market_narrative"]},
            "src4": {"base_url": "https://source4.example", "credibility_tier": 2, "tags": ["market_narrative"]},
        }
        store["c2"]["source_id"] = "src2"
        store["c3"]["source_id"] = "src3"
        store["c4"]["source_id"] = "src4"

        report = validate_synthesis(synthesis, store, source_registry=source_registry)

        self.assertEqual(report.removed_bullets, 1)
        self.assertEqual(report.synthesis["prevailing"][0]["citation_ids"], [])

    def test_numeric_claim_allows_two_independent_lower_tier_sources(self):
        synthesis = {
            "prevailing": [{"text": "Oil rose 3% on supply concerns.", "citation_ids": ["c1", "c2"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c3"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c4"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c5"]}],
        }
        store = {
            "c1": self._citation(
                "c1",
                url="https://publisher-a.example/oil",
                source_id="publisher_a",
                publisher="Publisher A",
            ),
            "c2": self._citation(
                "c2",
                url="https://publisher-b.example/oil",
                source_id="publisher_b",
                publisher="Publisher B",
            ),
            "c3": self._citation("c3", url="https://source3.example/doc", source_id="src3"),
            "c4": self._citation("c4", url="https://source4.example/doc", source_id="src4"),
            "c5": self._citation("c5", url="https://source5.example/doc", source_id="src5"),
        }
        source_registry = {
            "publisher_a": {"base_url": "https://publisher-a.example", "credibility_tier": 3, "tags": ["market_narrative"]},
            "publisher_b": {"base_url": "https://publisher-b.example", "credibility_tier": 3, "tags": ["market_narrative"]},
            "src3": {"base_url": "https://source3.example", "credibility_tier": 2, "tags": ["market_narrative"]},
            "src4": {"base_url": "https://source4.example", "credibility_tier": 2, "tags": ["market_narrative"]},
            "src5": {"base_url": "https://source5.example", "credibility_tier": 2, "tags": ["market_narrative"]},
        }

        report = validate_synthesis(synthesis, store, source_registry=source_registry)

        self.assertEqual(report.removed_bullets, 0)
        self.assertEqual(report.synthesis["prevailing"][0]["citation_ids"], ["c1", "c2"])

    def test_policy_claim_requires_tier_one_citation_when_official_source_exists_in_store(self):
        synthesis = {
            "prevailing": [{"text": "The Fed held rates steady.", "citation_ids": ["c1"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
        }
        store = {
            "c1": self._citation(
                "c1",
                url="https://reuters.example/fed",
                source_id="reuters_business",
                publisher="Reuters",
            ),
            "c2": self._citation("c2", url="https://source2.example/doc", source_id="src2"),
            "c3": self._citation("c3", url="https://source3.example/doc", source_id="src3"),
            "c4": self._citation("c4", url="https://source4.example/doc", source_id="src4"),
            "official": self._citation(
                "official",
                url="https://federalreserve.gov/newsevents/pressreleases/monetary20260310a.htm",
                source_id="fed_press_releases",
                publisher="Federal Reserve",
            ),
        }
        source_registry = {
            "reuters_business": {
                "base_url": "https://reuters.example",
                "credibility_tier": 2,
                "tags": ["market_narrative"],
            },
            "fed_press_releases": {
                "base_url": "https://federalreserve.gov/newsevents/pressreleases",
                "credibility_tier": 1,
                "tags": ["policy_centralbank", "rates", "us"],
            },
            "src2": {"base_url": "https://source2.example", "credibility_tier": 2, "tags": ["market_narrative"]},
            "src3": {"base_url": "https://source3.example", "credibility_tier": 2, "tags": ["market_narrative"]},
            "src4": {"base_url": "https://source4.example", "credibility_tier": 2, "tags": ["market_narrative"]},
        }

        report = validate_synthesis(synthesis, store, source_registry=source_registry)

        self.assertEqual(report.removed_bullets, 1)
        self.assertEqual(report.synthesis["prevailing"][0]["citation_ids"], [])

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
