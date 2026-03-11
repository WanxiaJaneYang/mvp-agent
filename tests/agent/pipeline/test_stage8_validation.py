import unittest

from apps.agent.pipeline.stage8_validation import run_stage8_citation_validation


class Stage8ValidationTests(unittest.TestCase):
    def test_stage8_retries_when_issue_centered_synthesis_has_no_issues(self):
        result = run_stage8_citation_validation({"issues": []}, {})

        self.assertEqual(result["status"], "retry")
        self.assertIn("issues", result["report"]["empty_core_sections"])

    def test_stage8_accepts_issue_centered_synthesis(self):
        synthesis = {
            "issues": [
                {
                    "issue_id": "issue_001",
                    "issue_question": "Will oil prices keep rising?",
                    "summary": "The market is split over near-term supply pressure.",
                    "prevailing": [{"text": "Supply risks support more upside.", "citation_ids": ["c1"]}],
                    "counter": [{"text": "Demand may soften soon.", "citation_ids": ["c2"]}],
                    "minority": [{"text": "Long-term upside may outlast the short-term move.", "citation_ids": ["c3"]}],
                    "watch": [{"text": "Watch inventory data.", "citation_ids": ["c4"]}],
                }
            ]
        }
        store = {
            "c1": {"id": "c1", "url": "u1", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c4": {"id": "c4", "url": "u4", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
        }

        result = run_stage8_citation_validation(synthesis, store)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["synthesis"]["issues"][0]["issue_id"], "issue_001")
        self.assertEqual(result["report"]["removed_bullets"], 0)

    def test_stage8_retries_when_issue_centered_synthesis_loses_core_section(self):
        synthesis = {
            "issues": [
                {
                    "issue_id": "issue_001",
                    "issue_question": "Will oil prices keep rising?",
                    "summary": "The market is split over near-term supply pressure.",
                    "prevailing": [{"text": "Supply risks support more upside.", "citation_ids": []}],
                    "counter": [{"text": "Demand may soften soon.", "citation_ids": ["c2"]}],
                    "minority": [{"text": "Long-term upside may outlast the short-term move.", "citation_ids": ["c3"]}],
                    "watch": [{"text": "Watch inventory data.", "citation_ids": ["c4"]}],
                }
            ]
        }
        store = {
            "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
            "c4": {"id": "c4", "url": "u4", "published_at": "2026-02-19T00:00:00Z", "paywall_policy": "full"},
        }

        result = run_stage8_citation_validation(synthesis, store, replace_with_placeholder=False)

        self.assertEqual(result["status"], "retry")
        self.assertIn("issue_001.prevailing", result["report"]["empty_core_sections"])
    def test_stage8_sets_ok_status_when_no_removals(self):
        synthesis = {
            "prevailing": [{"text": "Good", "citation_ids": ["c1"]}],
            "counter": [{"text": "Also good", "citation_ids": ["c2"]}],
            "minority": [{"text": "Still good", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch item", "citation_ids": ["c4"]}],
        }
        store = {
            "c1": {
                "id": "c1",
                "url": "u1",
                "published_at": "2026-02-19T00:00:00Z",
                "paywall_policy": "full",
            },
            "c2": {
                "id": "c2",
                "url": "u2",
                "published_at": "2026-02-19T00:00:00Z",
                "paywall_policy": "full",
            },
            "c3": {
                "id": "c3",
                "url": "u3",
                "published_at": "2026-02-19T00:00:00Z",
                "paywall_policy": "full",
            },
            "c4": {
                "id": "c4",
                "url": "u4",
                "published_at": "2026-02-19T00:00:00Z",
                "paywall_policy": "full",
            },
        }

        result = run_stage8_citation_validation(synthesis, store)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["report"]["removed_bullets"], 0)

    def test_stage8_sets_partial_status_on_removals(self):
        synthesis = {
            "prevailing": [
                {"text": "Bad", "citation_ids": []},
                {"text": "Good", "citation_ids": ["c4"]},
            ],
            "counter": [{"text": "ok", "citation_ids": ["c1"]}],
            "minority": [{"text": "ok", "citation_ids": ["c2"]}],
            "watch": [{"text": "ok", "citation_ids": ["c3"]}],
        }
        store = {
            "c1": {
                "id": "c1",
                "url": "u1",
                "published_at": "2026-02-19T00:00:00Z",
                "paywall_policy": "full",
            },
            "c2": {
                "id": "c2",
                "url": "u2",
                "published_at": "2026-02-19T00:00:00Z",
                "paywall_policy": "full",
            },
            "c3": {
                "id": "c3",
                "url": "u3",
                "published_at": "2026-02-19T00:00:00Z",
                "paywall_policy": "full",
            },
            "c4": {
                "id": "c4",
                "url": "u4",
                "published_at": "2026-02-19T00:00:00Z",
                "paywall_policy": "full",
            },
        }

        result = run_stage8_citation_validation(synthesis, store)

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["report"]["removed_bullets"], 1)

    def test_stage8_sets_retry_status_when_core_sections_empty(self):
        synthesis = {
            "prevailing": [],
            "counter": [],
            "minority": [],
            "watch": [],
        }
        store = {}

        result = run_stage8_citation_validation(synthesis, store)

        self.assertEqual(result["status"], "retry")

    def test_stage8_requires_tier_one_policy_citation_when_official_source_is_in_evidence_pack(
        self,
    ):
        synthesis = {
            "prevailing": [{"text": "The Fed held rates steady.", "citation_ids": ["c1"]}],
            "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
            "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
            "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
        }
        store = {
            "c1": {
                "citation_id": "c1",
                "url": "https://reuters.example/fed",
                "published_at": "2026-02-19T00:00:00Z",
                "source_id": "reuters_business",
                "paywall_policy": "full",
            },
            "c2": {
                "citation_id": "c2",
                "url": "https://source2.example/doc",
                "published_at": "2026-02-19T00:00:00Z",
                "source_id": "src2",
                "paywall_policy": "full",
            },
            "c3": {
                "citation_id": "c3",
                "url": "https://source3.example/doc",
                "published_at": "2026-02-19T00:00:00Z",
                "source_id": "src3",
                "paywall_policy": "full",
            },
            "c4": {
                "citation_id": "c4",
                "url": "https://source4.example/doc",
                "published_at": "2026-02-19T00:00:00Z",
                "source_id": "src4",
                "paywall_policy": "full",
            },
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
            "src2": {
                "base_url": "https://source2.example",
                "credibility_tier": 2,
                "tags": ["market_narrative"],
            },
            "src3": {
                "base_url": "https://source3.example",
                "credibility_tier": 2,
                "tags": ["market_narrative"],
            },
            "src4": {
                "base_url": "https://source4.example",
                "credibility_tier": 2,
                "tags": ["market_narrative"],
            },
        }

        result = run_stage8_citation_validation(
            synthesis,
            store,
            source_registry=source_registry,
            available_source_ids={"fed_press_releases", "reuters_business", "src2", "src3", "src4"},
        )

        self.assertEqual(result["status"], "retry")
        self.assertEqual(result["report"]["removed_bullets"], 1)
        self.assertEqual(result["synthesis"]["prevailing"][0]["citation_ids"], [])


if __name__ == "__main__":
    unittest.main()
