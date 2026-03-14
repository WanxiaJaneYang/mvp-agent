from __future__ import annotations

import unittest

from apps.agent.daily_brief.editorial_planner import build_corpus_summary, plan_brief_locally


class EditorialPlannerTests(unittest.TestCase):
    def test_plan_brief_uses_retained_summary_lines_for_bottom_line(self) -> None:
        plan = plan_brief_locally(
            run_id="run_demo",
            generated_at_utc="2026-03-12T07:05:00Z",
            corpus_summary=[
                "Growth data softened while payrolls still held up.",
                "Policy language remained cautious despite the softer data.",
                "Markets priced cuts more aggressively than officials did.",
            ],
            source_diversity_stats={"unique_publishers": 4},
            prior_brief_context=None,
        )

        self.assertEqual(
            plan["brief_thesis"],
            "Growth data softened while payrolls still held up. "
            "Policy language remained cautious despite the softer data.",
        )
        self.assertNotIn(plan["candidate_issue_seeds"][0], plan["brief_thesis"].lower())

    def test_plan_brief_falls_back_when_first_retained_summary_is_malformed(self) -> None:
        plan = plan_brief_locally(
            run_id="run_demo",
            generated_at_utc="2026-03-12T07:05:00Z",
            corpus_summary=[
                "growth growth growth growth",
                "Markets waited for clearer inflation evidence after the release.",
            ],
            source_diversity_stats={"unique_publishers": 2},
            prior_brief_context=None,
        )

        self.assertEqual(
            plan["brief_thesis"],
            "Markets waited for clearer inflation evidence after the release.",
        )
        self.assertNotEqual(plan["brief_thesis"], "growth growth growth growth")

    def test_plan_brief_keeps_readable_three_word_summary_lines(self) -> None:
        plan = plan_brief_locally(
            run_id="run_demo",
            generated_at_utc="2026-03-12T07:05:00Z",
            corpus_summary=[
                "Fed holds rates",
                "growth growth growth growth",
            ],
            source_diversity_stats={"unique_publishers": 2},
            prior_brief_context=None,
        )

        self.assertEqual(plan["brief_thesis"], "Fed holds rates.")

    def test_plan_brief_uses_full_mode_when_diversity_supports_two_issues(self) -> None:
        plan = plan_brief_locally(
            run_id="run_demo",
            generated_at_utc="2026-03-12T07:05:00Z",
            corpus_summary=[
                "Growth data softened while payrolls still held up.",
                "Policy language remained cautious despite the softer data.",
                "Markets priced cuts more aggressively than officials did.",
            ],
            source_diversity_stats={"unique_publishers": 4},
            prior_brief_context=None,
        )

        self.assertEqual(plan["render_mode"], "full")
        self.assertEqual(plan["issue_budget"], 2)
        self.assertEqual(plan["source_scarcity_mode"], "normal")

    def test_plan_brief_uses_compressed_mode_when_sources_are_sparse(self) -> None:
        plan = plan_brief_locally(
            run_id="run_demo",
            generated_at_utc="2026-03-12T07:05:00Z",
            corpus_summary=["One official release dominated the day."],
            source_diversity_stats={"unique_publishers": 1},
            prior_brief_context=None,
        )

        self.assertEqual(plan["render_mode"], "compressed")
        self.assertEqual(plan["issue_budget"], 1)
        self.assertEqual(plan["source_scarcity_mode"], "scarce")

    def test_build_corpus_summary_prefers_snippets_and_dedupes(self) -> None:
        summary = build_corpus_summary(
            corpus_items=[
                {"doc_id": "doc_001"},
                {"doc_id": "doc_002"},
                {"doc_id": "doc_003"},
            ],
            documents_by_id={
                "doc_001": {"rss_snippet": "Growth cooled.", "title": "Growth cooled.", "doc_id": "doc_001"},
                "doc_002": {
                    "rss_snippet": "Policy stayed cautious.",
                    "title": "Policy stayed cautious.",
                    "doc_id": "doc_002",
                },
                "doc_003": {"rss_snippet": "Growth cooled.", "title": "Growth cooled.", "doc_id": "doc_003"},
            },
        )

        self.assertEqual(summary, ["Growth cooled.", "Policy stayed cautious."])


if __name__ == "__main__":
    unittest.main()
