from __future__ import annotations

import inspect
import unittest
from typing import get_type_hints

from apps.agent.daily_brief.model_interfaces import (
    BriefPlannerInput,
    BriefPlannerProvider,
    ClaimComposerInput,
    ClaimComposerProvider,
    CriticInput,
    CriticProvider,
    IssuePlannerInput,
    IssuePlannerProvider,
)
from apps.agent.pipeline.types import CriticReport, IssueMap, StructuredClaim


class DailyBriefModelInterfaceTests(unittest.TestCase):
    def test_brief_planner_provider_is_task_specific(self) -> None:
        signature = inspect.signature(BriefPlannerProvider.plan_brief)
        self.assertIn("brief_input", signature.parameters)
        hints = get_type_hints(BriefPlannerProvider.plan_brief)
        self.assertEqual(hints["brief_input"], BriefPlannerInput)

    def test_issue_planner_provider_is_task_specific(self) -> None:
        signature = inspect.signature(IssuePlannerProvider.plan_issues)
        self.assertIn("brief_input", signature.parameters)
        hints = get_type_hints(IssuePlannerProvider.plan_issues)
        self.assertEqual(hints["brief_input"], IssuePlannerInput)
        self.assertEqual(hints["return"], list[IssueMap])

    def test_claim_composer_provider_is_task_specific(self) -> None:
        signature = inspect.signature(ClaimComposerProvider.compose_claims)
        self.assertIn("brief_input", signature.parameters)
        hints = get_type_hints(ClaimComposerProvider.compose_claims)
        self.assertEqual(hints["brief_input"], ClaimComposerInput)
        self.assertEqual(hints["return"], list[StructuredClaim])

    def test_critic_provider_is_task_specific(self) -> None:
        signature = inspect.signature(CriticProvider.review_brief)
        self.assertIn("brief_input", signature.parameters)
        hints = get_type_hints(CriticProvider.review_brief)
        self.assertEqual(hints["brief_input"], CriticInput)
        self.assertEqual(hints["return"], CriticReport)

    def test_interface_inputs_use_structured_context(self) -> None:
        self.assertEqual(
            set(BriefPlannerInput.__annotations__),
            {"run_id", "generated_at_utc", "corpus_summary", "source_diversity_stats", "prior_brief_context"},
        )
        self.assertEqual(
            set(IssuePlannerInput.__annotations__),
            {"run_id", "generated_at_utc", "brief_plan", "issue_evidence_scopes", "prior_brief_context"},
        )
        self.assertEqual(
            set(ClaimComposerInput.__annotations__),
            {
                "run_id",
                "generated_at_utc",
                "issue_map",
                "citation_store",
                "prior_brief_context",
            },
        )
        self.assertEqual(
            set(CriticInput.__annotations__),
            {
                "run_id",
                "generated_at_utc",
                "synthesis",
                "citation_store",
                "prior_brief_context",
            },
        )


if __name__ == "__main__":
    unittest.main()
