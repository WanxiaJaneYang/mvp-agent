from __future__ import annotations

import unittest

from apps.agent.daily_brief.issue_dedup import dedupe_issues


class IssueDedupTests(unittest.TestCase):
    def test_merges_high_overlap_issues(self) -> None:
        final_issues, overlap_reports, information_gain = dedupe_issues(
            issue_map=[
                {
                    "issue_id": "issue_001",
                    "issue_question": "Will softer growth change Fed expectations?",
                    "thesis_hint": "Growth is cooling while policy stays cautious.",
                    "supporting_evidence_ids": ["chunk_001", "chunk_002"],
                    "opposing_evidence_ids": [],
                    "minority_evidence_ids": [],
                    "watch_evidence_ids": [],
                },
                {
                    "issue_id": "issue_002",
                    "issue_question": "Will weaker growth shift Fed expectations soon?",
                    "thesis_hint": "Growth is cooling while policy stays cautious.",
                    "supporting_evidence_ids": ["chunk_001", "chunk_003"],
                    "opposing_evidence_ids": [],
                    "minority_evidence_ids": [],
                    "watch_evidence_ids": [],
                },
            ],
            brief_plan={
                "brief_id": "brief_2026-03-12",
                "brief_thesis": "Growth cooling is the main story.",
                "top_takeaways": [],
                "issue_budget": 2,
                "render_mode": "full",
                "source_scarcity_mode": "normal",
                "candidate_issue_seeds": [],
                "issue_order": [],
                "watchlist": [],
                "reason_codes": [],
            },
        )

        self.assertEqual(len(final_issues), 1)
        self.assertEqual(overlap_reports[0]["decision"], "merge")
        self.assertEqual(information_gain[-1]["decision"], "drop")

    def test_drops_low_information_gain_third_issue(self) -> None:
        final_issues, _overlap_reports, information_gain = dedupe_issues(
            issue_map=[
                {
                    "issue_id": "issue_001",
                    "issue_question": "Will softer growth change Fed expectations?",
                    "thesis_hint": "Growth is cooling.",
                    "supporting_evidence_ids": ["chunk_001"],
                    "opposing_evidence_ids": [],
                    "minority_evidence_ids": [],
                    "watch_evidence_ids": [],
                },
                {
                    "issue_id": "issue_002",
                    "issue_question": "Will policy language stay cautious?",
                    "thesis_hint": "Policy remains cautious.",
                    "supporting_evidence_ids": ["chunk_010"],
                    "opposing_evidence_ids": [],
                    "minority_evidence_ids": [],
                    "watch_evidence_ids": [],
                },
                {
                    "issue_id": "issue_003",
                    "issue_question": "Will softer growth change Fed expectations again?",
                    "thesis_hint": "Growth is cooling.",
                    "supporting_evidence_ids": ["chunk_001"],
                    "opposing_evidence_ids": [],
                    "minority_evidence_ids": [],
                    "watch_evidence_ids": [],
                },
            ],
            brief_plan={
                "brief_id": "brief_2026-03-12",
                "brief_thesis": "Two real debates, not three.",
                "top_takeaways": [],
                "issue_budget": 2,
                "render_mode": "full",
                "source_scarcity_mode": "normal",
                "candidate_issue_seeds": [],
                "issue_order": [],
                "watchlist": [],
                "reason_codes": [],
            },
        )

        self.assertEqual(len(final_issues), 2)
        self.assertEqual(information_gain[-1]["decision"], "drop")

    def test_budget_cap_runs_after_information_gain_so_stronger_later_issue_can_survive(self) -> None:
        final_issues, _overlap_reports, information_gain = dedupe_issues(
            issue_map=[
                {
                    "issue_id": "issue_001",
                    "issue_question": "Will softer growth change Fed expectations?",
                    "thesis_hint": "Growth is cooling.",
                    "supporting_evidence_ids": ["chunk_001"],
                    "opposing_evidence_ids": [],
                    "minority_evidence_ids": [],
                    "watch_evidence_ids": [],
                },
                {
                    "issue_id": "issue_002",
                    "issue_question": "Will policy language stay cautious as inflation stays sticky?",
                    "thesis_hint": "Policy remains cautious while inflation stays sticky.",
                    "supporting_evidence_ids": ["chunk_010", "chunk_011", "chunk_012"],
                    "opposing_evidence_ids": [],
                    "minority_evidence_ids": [],
                    "watch_evidence_ids": [],
                },
            ],
            brief_plan={
                "brief_id": "brief_2026-03-12",
                "brief_thesis": "Only one issue should survive.",
                "top_takeaways": [],
                "issue_budget": 1,
                "render_mode": "compressed",
                "source_scarcity_mode": "scarce",
                "candidate_issue_seeds": [],
                "issue_order": [],
                "watchlist": [],
                "reason_codes": [],
            },
        )

        self.assertEqual([issue["issue_id"] for issue in final_issues], ["issue_002"])
        self.assertEqual(information_gain[0]["decision"], "drop")
        self.assertEqual(information_gain[0]["reason_codes"], ["issue_budget_exceeded"])
        self.assertEqual(information_gain[1]["decision"], "keep")


if __name__ == "__main__":
    unittest.main()
