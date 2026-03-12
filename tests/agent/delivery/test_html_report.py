import tempfile
import unittest
from pathlib import Path

from apps.agent.delivery.html_report import render_daily_brief_html


class HtmlReportTests(unittest.TestCase):
    def test_render_daily_brief_html_renders_issue_centered_review_with_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "artifacts" / "daily" / "2026-03-10" / "brief.html"

            result = render_daily_brief_html(
                output_path=output_path,
                report_date="2026-03-10",
                run_id="run_daily_fixture",
                synthesis={
                    "brief": {
                        "bottom_line": "Supply pressure and demand softness are the two main debates.",
                        "top_takeaways": [
                            "Supply pressure remains live.",
                            "Demand softness may cap the move.",
                        ],
                        "watchlist": ["Watch OPEC guidance next week."],
                        "render_mode": "full",
                        "source_scarcity_mode": "normal",
                        "issue_budget": 2,
                    },
                    "issues": [
                        {
                            "issue_id": "issue_001",
                            "issue_question": "Will oil prices keep rising over the next few weeks?",
                            "summary": (
                                "The evidence is split between short-term supply pressure "
                                "and softer demand expectations."
                            ),
                            "prevailing": [
                                {
                                    "text": "The prevailing argument emphasizes near-term supply pressure.",
                                    "citation_ids": ["cite_001"],
                                    "evidence": [
                                        {
                                            "citation_id": "cite_001",
                                            "publisher": "Reuters",
                                            "published_at": "2026-03-10T14:00:00Z",
                                            "support_text": "Supply disruptions stayed in focus for oil traders.",
                                        }
                                    ],
                                }
                            ],
                            "counter": [
                                {
                                    "text": "The main counterargument stresses softer demand expectations.",
                                    "citation_ids": ["cite_002"],
                                    "evidence": [
                                        {
                                            "citation_id": "cite_002",
                                            "publisher": "Wall Street Journal",
                                            "published_at": "2026-03-10T15:00:00Z",
                                            "support_text": "Demand concerns may cap the rally.",
                                        }
                                    ],
                                }
                            ],
                            "minority": [
                                {
                                    "text": "A minority view looks further out.",
                                    "citation_ids": ["cite_003"],
                                    "evidence": [],
                                }
                            ],
                            "watch": [
                                {
                                    "text": "Watch OPEC guidance next week.",
                                    "citation_ids": ["cite_004"],
                                    "evidence": [],
                                }
                            ],
                        }
                    ]
                },
                citation_store={
                    "cite_001": {"title": "Reuters oil item", "url": "https://example.test/reuters"},
                    "cite_002": {"title": "WSJ oil item", "url": "https://example.test/wsj"},
                    "cite_003": {"title": "Fed oil item", "url": "https://example.test/fed"},
                    "cite_004": {"title": "BEA oil item", "url": "https://example.test/bea"},
                },
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertEqual(result, output_path)
        self.assertIn("Bottom Line", html)
        self.assertIn("Key Takeaways", html)
        self.assertIn("Will oil prices keep rising over the next few weeks?", html)
        self.assertIn("What to Watch", html)
        self.assertIn("Supply disruptions stayed in focus for oil traders.", html)
        self.assertIn("https://example.test/reuters", html)

    def test_render_daily_brief_html_writes_core_sections_and_citations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "artifacts" / "daily" / "2026-03-10" / "brief.html"

            result = render_daily_brief_html(
                output_path=output_path,
                report_date="2026-03-10",
                run_id="run_daily_fixture",
                synthesis={
                    "prevailing": [
                        {"text": "Fed kept policy steady.", "citation_ids": ["cite_001"]}
                    ],
                    "counter": [
                        {"text": "Growth is cooling faster.", "citation_ids": ["cite_002"]}
                    ],
                    "minority": [
                        {"text": "Some investors expect a rebound.", "citation_ids": ["cite_003"]}
                    ],
                    "watch": [{"text": "Watch payroll revisions.", "citation_ids": ["cite_004"]}],
                },
                citation_store={
                    "cite_001": {"title": "Fed release", "url": "https://example.test/fed"},
                    "cite_002": {"title": "Reuters item", "url": "https://example.test/reuters"},
                    "cite_003": {"title": "WSJ item", "url": "https://example.test/wsj"},
                    "cite_004": {"title": "BLS item", "url": "https://example.test/bls"},
                },
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertEqual(result, output_path)
        self.assertIn("Daily Brief", html)
        self.assertIn("2026-03-10", html)
        self.assertIn("Prevailing", html)
        self.assertIn("Counter", html)
        self.assertIn("Minority", html)
        self.assertIn("Watch", html)
        self.assertIn("cite_001", html)
        self.assertIn("https://example.test/fed", html)

    def test_render_daily_brief_html_makes_abstained_output_explicit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "artifacts" / "daily" / "2026-03-10" / "brief.html"

            render_daily_brief_html(
                output_path=output_path,
                report_date="2026-03-10",
                run_id="run_abstain",
                synthesis={
                    "prevailing": [
                        {
                            "text": "[Insufficient evidence to produce a validated output]",
                            "citation_ids": [],
                        }
                    ],
                    "counter": [
                        {
                            "text": "[Insufficient evidence to produce a validated output]",
                            "citation_ids": [],
                        }
                    ],
                    "minority": [
                        {
                            "text": "[Insufficient evidence to produce a validated output]",
                            "citation_ids": [],
                        }
                    ],
                    "watch": [
                        {
                            "text": "[Insufficient evidence to produce a validated output]",
                            "citation_ids": [],
                        }
                    ],
                },
                citation_store={},
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Abstained", html)
        self.assertIn("Insufficient evidence", html)

    def test_render_daily_brief_html_renders_changed_section_only_when_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "artifacts" / "daily" / "2026-03-10" / "brief.html"

            render_daily_brief_html(
                output_path=output_path,
                report_date="2026-03-10",
                run_id="run_changed",
                synthesis={
                    "prevailing": [
                        {"text": "Fed kept policy steady.", "citation_ids": ["cite_001"]}
                    ],
                    "counter": [
                        {"text": "Growth is cooling faster.", "citation_ids": ["cite_002"]}
                    ],
                    "minority": [
                        {"text": "Some investors expect a rebound.", "citation_ids": ["cite_003"]}
                    ],
                    "watch": [{"text": "Watch payroll revisions.", "citation_ids": ["cite_004"]}],
                    "changed": [
                        {
                            "text": "Prevailing changed versus yesterday: Fed kept policy steady.",
                            "citation_ids": ["cite_001"],
                        }
                    ],
                },
                citation_store={
                    "cite_001": {"title": "Fed release", "url": "https://example.test/fed"},
                    "cite_002": {"title": "Reuters item", "url": "https://example.test/reuters"},
                    "cite_003": {"title": "WSJ item", "url": "https://example.test/wsj"},
                    "cite_004": {"title": "BLS item", "url": "https://example.test/bls"},
                },
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Changed Since Yesterday", html)
        self.assertIn("Prevailing changed versus yesterday", html)


if __name__ == "__main__":
    unittest.main()
