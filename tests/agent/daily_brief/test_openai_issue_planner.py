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
                brief_plan={
                    "brief_id": "brief_2026-03-12_run_001",
                    "brief_thesis": "Supply pressure and softer demand are the two main debates today.",
                    "top_takeaways": ["Supply pressure remained live."],
                    "issue_budget": 2,
                    "render_mode": "full",
                    "source_scarcity_mode": "normal",
                    "candidate_issue_seeds": ["supply pressure", "demand softness"],
                    "issue_order": ["seed_001", "seed_002"],
                    "watchlist": ["Watch inventories next week."],
                    "reason_codes": ["two_distinct_debates_supported"],
                },
                issue_evidence_scopes=[
                    {
                        "issue_id": "issue_oil",
                        "primary_chunk_ids": ["chunk_1", "chunk_2"],
                        "opposing_chunk_ids": ["chunk_3"],
                        "minority_chunk_ids": ["chunk_4"],
                        "watch_chunk_ids": ["chunk_5"],
                        "coverage_summary": {
                            "unique_publishers": 5,
                            "source_roles": ["official", "market_media"],
                            "time_span_hours": 18,
                        },
                    }
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
        self.assertIn("up to 2 issue-centered", captured_request["messages"][0]["content"])
        self.assertIn("up to 2 issue-centered", captured_request["messages"][1]["content"])
        self.assertEqual(captured_request["response_format"]["json_schema"]["schema"]["maxItems"], 2)
        self.assertIn("brief_plan", captured_request["input"])
        self.assertEqual(len(captured_request["input"]["issue_evidence_scopes"]), 1)
        self.assertEqual(
            set(captured_request["input"]["issue_evidence_scopes"][0]),
            {
                "issue_id",
                "primary_chunk_ids",
                "opposing_chunk_ids",
                "minority_chunk_ids",
                "watch_chunk_ids",
                "coverage_summary",
            },
        )
        self.assertLessEqual(len(captured_request["input"]["prior_brief_context"]["oversized"]), 240)

    def test_request_payload_tracks_single_issue_budget(self) -> None:
        captured_request: dict[str, object] = {}

        def loader(request_payload):
            captured_request.update(request_payload)
            return [
                {
                    "issue_id": "issue_oil",
                    "issue_question": "Will oil prices keep rising over the next few weeks?",
                    "thesis_hint": "Supply concerns are keeping near-term pressure skewed upward.",
                    "supporting_evidence_ids": ["chunk_1"],
                    "opposing_evidence_ids": [],
                    "minority_evidence_ids": [],
                    "watch_evidence_ids": [],
                }
            ]

        planner = OpenAIIssuePlanner(response_loader=loader)
        planner.plan_issues(
            brief_input=IssuePlannerInput(
                run_id="run_001",
                generated_at_utc="2026-03-12T00:00:00Z",
                brief_plan={
                    "brief_id": "brief_2026-03-12_run_001",
                    "brief_thesis": "Supply pressure is the main debate.",
                    "top_takeaways": [],
                    "issue_budget": 1,
                    "render_mode": "compressed",
                    "source_scarcity_mode": "scarce",
                    "candidate_issue_seeds": ["supply pressure"],
                    "issue_order": ["seed_001"],
                    "watchlist": [],
                    "reason_codes": ["source_scarcity_detected"],
                },
                issue_evidence_scopes=[
                    {
                        "issue_id": "issue_oil",
                        "primary_chunk_ids": ["chunk_1"],
                        "opposing_chunk_ids": [],
                        "minority_chunk_ids": [],
                        "watch_chunk_ids": [],
                        "coverage_summary": {
                            "unique_publishers": 1,
                            "source_roles": ["market_media"],
                            "time_span_hours": 0,
                        },
                    }
                ],
                prior_brief_context=None,
            )
        )

        self.assertEqual(captured_request["response_format"]["json_schema"]["schema"]["maxItems"], 1)
        self.assertIn("up to 1 issue-centered", captured_request["messages"][0]["content"])

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
                brief_plan={
                    "brief_id": "brief_2026-03-12_run_001",
                    "brief_thesis": "Supply pressure and softer demand are the two main debates today.",
                    "top_takeaways": ["Supply pressure remained live."],
                    "issue_budget": 2,
                    "render_mode": "full",
                    "source_scarcity_mode": "normal",
                    "candidate_issue_seeds": ["supply pressure", "demand softness"],
                    "issue_order": ["seed_001", "seed_002"],
                    "watchlist": ["Watch inventories next week."],
                    "reason_codes": ["two_distinct_debates_supported"],
                },
                issue_evidence_scopes=[
                    {
                        "issue_id": "issue_oil",
                        "primary_chunk_ids": ["chunk_1", "chunk_2"],
                        "opposing_chunk_ids": ["chunk_3"],
                        "minority_chunk_ids": ["chunk_4"],
                        "watch_chunk_ids": ["chunk_5"],
                        "coverage_summary": {
                            "unique_publishers": 5,
                            "source_roles": ["official", "market_media"],
                            "time_span_hours": 18,
                        },
                    }
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
                    brief_plan={
                        "brief_id": "brief_2026-03-12_run_001",
                        "brief_thesis": "Supply pressure is the main debate.",
                        "top_takeaways": [],
                        "issue_budget": 1,
                        "render_mode": "compressed",
                        "source_scarcity_mode": "scarce",
                        "candidate_issue_seeds": ["supply pressure"],
                        "issue_order": ["seed_001"],
                        "watchlist": [],
                        "reason_codes": ["source_scarcity_detected"],
                    },
                    issue_evidence_scopes=[],
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
                    brief_plan={
                        "brief_id": "brief_2026-03-12_run_001",
                        "brief_thesis": "Supply pressure is the main debate.",
                        "top_takeaways": [],
                        "issue_budget": 1,
                        "render_mode": "compressed",
                        "source_scarcity_mode": "scarce",
                        "candidate_issue_seeds": ["supply pressure"],
                        "issue_order": ["seed_001"],
                        "watchlist": [],
                        "reason_codes": ["source_scarcity_detected"],
                    },
                    issue_evidence_scopes=[],
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
                    brief_plan={
                        "brief_id": "brief_2026-03-12_run_001",
                        "brief_thesis": "Supply pressure is the main debate.",
                        "top_takeaways": [],
                        "issue_budget": 1,
                        "render_mode": "compressed",
                        "source_scarcity_mode": "scarce",
                        "candidate_issue_seeds": ["supply pressure"],
                        "issue_order": ["seed_001"],
                        "watchlist": [],
                        "reason_codes": ["source_scarcity_detected"],
                    },
                    issue_evidence_scopes=[],
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
                    brief_plan={
                        "brief_id": "brief_2026-03-12_run_001",
                        "brief_thesis": "Supply pressure is the main debate.",
                        "top_takeaways": [],
                        "issue_budget": 1,
                        "render_mode": "compressed",
                        "source_scarcity_mode": "scarce",
                        "candidate_issue_seeds": ["supply pressure"],
                        "issue_order": ["seed_001"],
                        "watchlist": [],
                        "reason_codes": ["source_scarcity_detected"],
                    },
                    issue_evidence_scopes=[
                        {
                            "issue_id": "issue_oil",
                            "primary_chunk_ids": ["chunk_1"],
                            "opposing_chunk_ids": [],
                            "minority_chunk_ids": [],
                            "watch_chunk_ids": [],
                            "coverage_summary": {
                                "unique_publishers": 1,
                                "source_roles": ["market_media"],
                                "time_span_hours": 0,
                            },
                        }
                    ],
                    prior_brief_context=None,
                )
            )


if __name__ == "__main__":
    unittest.main()
