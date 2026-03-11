from __future__ import annotations

import unittest

from apps.agent.daily_brief.model_interfaces import IssuePlannerInput
from apps.agent.daily_brief.openai_issue_planner import OpenAIIssuePlanner


class OpenAIIssuePlannerTests(unittest.TestCase):
    def test_plans_issues_from_schema_valid_json(self) -> None:
        planner = OpenAIIssuePlanner(
            response_loader=lambda _brief_input: """
            [
              {
                "issue_id": "issue_oil",
                "issue_question": "Will oil prices keep rising over the next few weeks?",
                "thesis_hint": "Supply concerns are keeping near-term pressure skewed upward.",
                "supporting_evidence_ids": ["chunk_1", "chunk_2"],
                "opposing_evidence_ids": ["chunk_3"],
                "minority_evidence_ids": ["chunk_4"],
                "watch_evidence_ids": ["chunk_5"]
              }
            ]
            """
        )

        result = planner.plan_issues(
            brief_input=IssuePlannerInput(
                run_id="run_001",
                generated_at_utc="2026-03-12T00:00:00Z",
                evidence_pack=[{"chunk_id": "chunk_1"}],
                prior_brief_context=None,
            )
        )

        self.assertEqual(result[0]["issue_id"], "issue_oil")
        self.assertEqual(result[0]["supporting_evidence_ids"], ["chunk_1", "chunk_2"])

    def test_rejects_malformed_issue_map_output(self) -> None:
        planner = OpenAIIssuePlanner(response_loader=lambda _brief_input: '[{"issue_id": "missing_fields"}]')

        with self.assertRaises(ValueError):
            planner.plan_issues(
                brief_input=IssuePlannerInput(
                    run_id="run_001",
                    generated_at_utc="2026-03-12T00:00:00Z",
                    evidence_pack=[],
                    prior_brief_context=None,
                )
            )

    def test_rejects_wrong_issue_map_field_types(self) -> None:
        planner = OpenAIIssuePlanner(
            response_loader=lambda _brief_input: """
            [
              {
                "issue_id": "issue_oil",
                "issue_question": "Will oil prices keep rising over the next few weeks?",
                "thesis_hint": "Supply concerns are keeping near-term pressure skewed upward.",
                "supporting_evidence_ids": "chunk_1",
                "opposing_evidence_ids": ["chunk_3"],
                "minority_evidence_ids": ["chunk_4"],
                "watch_evidence_ids": ["chunk_5"]
              }
            ]
            """
        )

        with self.assertRaises(ValueError):
            planner.plan_issues(
                brief_input=IssuePlannerInput(
                    run_id="run_001",
                    generated_at_utc="2026-03-12T00:00:00Z",
                    evidence_pack=[],
                    prior_brief_context=None,
                )
            )


if __name__ == "__main__":
    unittest.main()
