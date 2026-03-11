from __future__ import annotations

import unittest

from apps.agent.daily_brief.prior_brief_context import build_prior_brief_context


class PriorBriefContextTests(unittest.TestCase):
    def test_extracts_bounded_context_from_previous_synthesis(self) -> None:
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
        self.assertEqual(context["citation_ids"], ["cite_001", "cite_002"])

    def test_returns_none_when_previous_synthesis_missing(self) -> None:
        self.assertIsNone(
            build_prior_brief_context(
                previous_synthesis=None,
                previous_generated_at_utc=None,
            )
        )


if __name__ == "__main__":
    unittest.main()
