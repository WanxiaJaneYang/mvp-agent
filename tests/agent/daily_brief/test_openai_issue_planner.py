from __future__ import annotations

import unittest

from apps.agent.daily_brief.model_interfaces import IssuePlannerInput
from apps.agent.daily_brief.openai_issue_planner import OpenAIIssuePlanner


class OpenAIIssuePlannerTests(unittest.TestCase):
    def test_builds_bounded_structured_request_payload_before_parsing(self) -> None:
        captured_request: dict[str, object] = {}

        def loader(request_payload):
            captured_request.update(request_payload)
            return {
                "output_text": """
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
            }

        planner = OpenAIIssuePlanner(response_loader=loader)

        result = planner.plan_issues(
            brief_input=IssuePlannerInput(
                run_id="run_001",
                generated_at_utc="2026-03-12T00:00:00Z",
                evidence_pack=[
                    {
                        "chunk_id": "chunk_1",
                        "doc_id": "doc_1",
                        "publisher": "Reuters",
                        "title": "Oil rises on supply concerns",
                        "text": "Supply concerns kept oil prices supported as traders watched shipping disruptions.",
                        "retrieval_score": 0.91,
                    },
                    {
                        "chunk_id": "chunk_2",
                        "doc_id": "doc_2",
                        "publisher": "WSJ",
                        "text": "Refiners are watching inventory pressure.",
                    },
                    {
                        "chunk_id": "chunk_3",
                        "doc_id": "doc_3",
                        "publisher": "BLS",
                        "text": "Demand indicators softened.",
                    },
                    {
                        "chunk_id": "chunk_4",
                        "doc_id": "doc_4",
                        "publisher": "BEA",
                        "text": "Long-term consumption remains firm.",
                    },
                    {
                        "chunk_id": "chunk_5",
                        "doc_id": "doc_5",
                        "publisher": "EIA",
                        "text": "Watch inventory data next week.",
                    },
                ],
                prior_brief_context={
                    "prior_issue_questions": ["Will oil prices keep rising?"],
                    "prior_generated_at_utc": "2026-03-11T00:00:00Z",
                    "oversized": "x" * 600,
                },
            )
        )

        self.assertEqual(result[0]["issue_id"], "issue_oil")
        self.assertEqual(captured_request["task"], "daily_brief_issue_planner")
        self.assertEqual(captured_request["run_id"], "run_001")
        self.assertEqual(captured_request["generated_at_utc"], "2026-03-12T00:00:00Z")
        self.assertEqual(captured_request["response_format"]["type"], "json_schema")
        self.assertEqual(captured_request["messages"][0]["role"], "system")
        self.assertEqual(len(captured_request["input"]["evidence_pack"]), 5)
        self.assertEqual(
            set(captured_request["input"]["evidence_pack"][0]),
            {"chunk_id", "doc_id", "publisher", "title", "text", "retrieval_score"},
        )
        self.assertLessEqual(len(captured_request["input"]["prior_brief_context"]["oversized"]), 240)

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
                evidence_pack=[
                    {"chunk_id": "chunk_1"},
                    {"chunk_id": "chunk_2"},
                    {"chunk_id": "chunk_3"},
                    {"chunk_id": "chunk_4"},
                    {"chunk_id": "chunk_5"},
                ],
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

    def test_rejects_empty_issue_list_output(self) -> None:
        planner = OpenAIIssuePlanner(response_loader=lambda _request_payload: "[]")

        with self.assertRaises(ValueError):
            planner.plan_issues(
                brief_input=IssuePlannerInput(
                    run_id="run_001",
                    generated_at_utc="2026-03-12T00:00:00Z",
                    evidence_pack=[],
                    prior_brief_context=None,
                )
            )

    def test_rejects_issue_output_that_references_unknown_evidence_ids(self) -> None:
        planner = OpenAIIssuePlanner(
            response_loader=lambda _request_payload: """
            [
              {
                "issue_id": "issue_oil",
                "issue_question": "Will oil prices keep rising over the next few weeks?",
                "thesis_hint": "Supply concerns are keeping near-term pressure skewed upward.",
                "supporting_evidence_ids": ["chunk_404"],
                "opposing_evidence_ids": [],
                "minority_evidence_ids": [],
                "watch_evidence_ids": []
              }
            ]
            """
        )

        with self.assertRaises(ValueError):
            planner.plan_issues(
                brief_input=IssuePlannerInput(
                    run_id="run_001",
                    generated_at_utc="2026-03-12T00:00:00Z",
                    evidence_pack=[{"chunk_id": "chunk_1"}],
                    prior_brief_context=None,
                )
            )


if __name__ == "__main__":
    unittest.main()
