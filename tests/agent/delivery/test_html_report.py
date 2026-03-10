import tempfile
import unittest
from pathlib import Path

from apps.agent.delivery.html_report import render_daily_brief_html


class HtmlReportTests(unittest.TestCase):
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
