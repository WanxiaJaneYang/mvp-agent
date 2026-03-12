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
                    "issues": [
                        {
                            "issue_id": "issue_001",
                            "title": "Will oil prices keep rising over the next few weeks?",
                            "summary": "The evidence is split between short-term supply pressure and softer demand expectations.",
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
                                    "text": "A minority view argues the longer-term move can stay firm without a sharp short-term spike.",
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
        self.assertIn("Daily Brief", html)
        self.assertIn("Will oil prices keep rising over the next few weeks?", html)
        self.assertIn("Prevailing", html)
        self.assertIn("Counter", html)
        self.assertIn("Minority", html)
        self.assertIn("What to Watch", html)
        self.assertIn("Supply disruptions stayed in focus for oil traders.", html)
        self.assertIn("cite_001", html)
        self.assertIn("https://example.test/reuters", html)

    def test_render_daily_brief_html_makes_issue_centered_abstained_output_explicit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "artifacts" / "daily" / "2026-03-10" / "brief.html"

            render_daily_brief_html(
                output_path=output_path,
                report_date="2026-03-10",
                run_id="run_abstain",
                synthesis={
                    "issues": [
                        {
                            "issue_id": "issue_001",
                            "title": "Insufficient evidence for a validated issue review",
                            "summary": "The available evidence did not support a full literature review.",
                            "prevailing": [{"text": "[Insufficient evidence to produce a validated output]", "citation_ids": []}],
                            "counter": [{"text": "[Insufficient evidence to produce a validated output]", "citation_ids": []}],
                            "minority": [{"text": "[Insufficient evidence to produce a validated output]", "citation_ids": []}],
                            "watch": [{"text": "[Insufficient evidence to produce a validated output]", "citation_ids": []}],
                        }
                    ],
                    "meta": {"status": "abstained"},
                },
                citation_store={},
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Abstained", html)
        self.assertIn("Insufficient evidence", html)


if __name__ == "__main__":
    unittest.main()
