from __future__ import annotations

import unittest

from apps.agent.daily_brief.prior_brief_context import build_prior_brief_context


class PriorBriefContextTests(unittest.TestCase):
    def test_extracts_bounded_context_from_flat_previous_synthesis(self) -> None:
        previous_synthesis = {
            "prevailing": [{"text": "Prevailing claim.", "citation_ids": ["cite_001"]}],
            "counter": [{"text": "Counter claim.", "citation_ids": ["cite_002"]}],
            "changed": [{"text": "Changed claim.", "citation_ids": ["cite_003"]}],
        }

        context = build_prior_brief_context(
            previous_synthesis=previous_synthesis,
            previous_generated_at_utc="2026-03-11T00:00:00Z",
        )

        self.assertEqual(context["previous_generated_at_utc"], "2026-03-11T00:00:00Z")
        self.assertEqual(context["claim_summaries"], ["Prevailing claim.", "Counter claim."])
        self.assertEqual(context["claim_texts"], ["Prevailing claim.", "Counter claim."])
        self.assertEqual(context["citation_ids"], ["cite_001", "cite_002"])
        self.assertEqual(context["issue_questions"], ["Previous daily brief"])
        self.assertEqual(context["source_refs"], [])
        self.assertEqual(context["issues"][0]["issue_question"], "Previous daily brief")
        self.assertEqual(context["issues"][0]["claim_summaries"], ["Prevailing claim.", "Counter claim."])

    def test_extracts_issue_centered_prior_questions_claims_and_source_refs(self) -> None:
        previous_synthesis = {
            "issues": [
                {
                    "issue_id": "issue_oil",
                    "issue_question": "Will oil prices keep rising over the next few weeks?",
                    "summary": "The prior brief leaned bullish on supply pressure.",
                    "prevailing": [
                        {
                            "text": "Supply risks kept the short-term bias upward.",
                            "citation_ids": ["cite_001"],
                            "evidence": [
                                {
                                    "citation_id": "cite_001",
                                    "publisher": "Reuters",
                                    "published_at": "2026-03-11T01:00:00Z",
                                    "support_text": "Supply disruptions stayed in focus.",
                                }
                            ],
                        }
                    ],
                    "counter": [
                        {
                            "text": "Demand concerns could cap the move.",
                            "citation_ids": ["cite_002"],
                            "evidence": [
                                {
                                    "citation_id": "cite_002",
                                    "publisher": "WSJ",
                                    "published_at": "2026-03-11T02:00:00Z",
                                    "support_text": "Demand concerns may cap the rally.",
                                }
                            ],
                        }
                    ],
                    "minority": [],
                    "watch": [],
                }
            ]
        }

        context = build_prior_brief_context(
            previous_synthesis=previous_synthesis,
            previous_generated_at_utc="2026-03-11T07:05:00Z",
        )

        self.assertEqual(context["previous_generated_at_utc"], "2026-03-11T07:05:00Z")
        self.assertEqual(context["issue_count"], 1)
        self.assertEqual(context["issues"][0]["issue_id"], "issue_oil")
        self.assertEqual(
            context["issues"][0]["issue_question"],
            "Will oil prices keep rising over the next few weeks?",
        )
        self.assertEqual(
            context["issues"][0]["claim_summaries"],
            [
                "Supply risks kept the short-term bias upward.",
                "Demand concerns could cap the move.",
            ],
        )
        self.assertEqual(context["issues"][0]["citation_ids"], ["cite_001", "cite_002"])
        self.assertEqual(
            context["issue_questions"],
            ["Will oil prices keep rising over the next few weeks?"],
        )
        self.assertEqual(
            context["claim_texts"],
            [
                "Supply risks kept the short-term bias upward.",
                "Demand concerns could cap the move.",
            ],
        )
        self.assertEqual(
            context["issues"][0]["source_refs"],
            [
                "Reuters @ 2026-03-11T01:00:00Z",
                "WSJ @ 2026-03-11T02:00:00Z",
            ],
        )
        self.assertEqual(
            context["source_refs"],
            [
                "Reuters @ 2026-03-11T01:00:00Z",
                "WSJ @ 2026-03-11T02:00:00Z",
            ],
        )

    def test_bounds_issue_centered_context_to_three_issues_and_two_claims_per_issue(self) -> None:
        previous_synthesis = {
            "issues": [
                {
                    "issue_id": f"issue_{index}",
                    "issue_question": f"Issue question {index}",
                    "prevailing": [{"text": f"Prevailing {index}", "citation_ids": [f"cite_p_{index}"]}],
                    "counter": [{"text": f"Counter {index}", "citation_ids": [f"cite_c_{index}"]}],
                    "minority": [{"text": f"Minority {index}", "citation_ids": [f"cite_m_{index}"]}],
                    "watch": [{"text": f"Watch {index}", "citation_ids": [f"cite_w_{index}"]}],
                }
                for index in range(1, 5)
            ]
        }

        context = build_prior_brief_context(
            previous_synthesis=previous_synthesis,
            previous_generated_at_utc="2026-03-11T07:05:00Z",
        )

        self.assertEqual(context["issue_count"], 3)
        self.assertEqual([issue["issue_id"] for issue in context["issues"]], ["issue_1", "issue_2", "issue_3"])
        self.assertEqual(
            context["issues"][0]["claim_summaries"],
            ["Prevailing 1", "Counter 1"],
        )
        self.assertEqual(len(context["claim_summaries"]), 6)

    def test_returns_none_when_previous_synthesis_missing(self) -> None:
        self.assertIsNone(
            build_prior_brief_context(
                previous_synthesis=None,
                previous_generated_at_utc=None,
            )
        )


if __name__ == "__main__":
    unittest.main()
