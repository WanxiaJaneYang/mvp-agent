import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts import validate_artifacts


class ArtifactValidationTests(unittest.TestCase):
    def test_planned_ticket_with_all_listed_files_present_fails_semantic_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "apps" / "agent" / "delivery").mkdir(parents=True)
            (root / "scripts").mkdir(parents=True)
            (root / "docs").mkdir(parents=True)
            (root / "artifacts" / "modelling").mkdir(parents=True)
            (root / "artifacts" / "runtime").mkdir(parents=True)

            (root / "apps" / "agent" / "delivery" / "html_report.py").write_text("", encoding="utf-8")
            (root / "scripts" / "run_daily_brief_fixture.py").write_text("", encoding="utf-8")
            (root / "artifacts" / "modelling" / "backlog.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "generated_on": "2026-03-10",
                        "phase": "implementation",
                        "tickets": [
                            {
                                "id": "M007",
                                "title": "Implement daily brief delivery",
                                "status": "planned",
                                "priority": "P1",
                                "depends_on": ["M004"],
                                "files": [
                                    "apps/agent/delivery/html_report.py",
                                    "scripts/run_daily_brief_fixture.py",
                                ],
                                "acceptance_criteria": ["Daily brief local HTML output generated in stable structure"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "artifacts" / "modelling" / "source_registry.yaml").write_text("sources: []\n", encoding="utf-8")
            (root / "artifacts" / "runtime" / "v1_active_sources.yaml").write_text(
                "active_source_ids: []\n", encoding="utf-8"
            )
            (root / "docs" / "status-matrix.md").write_text(
                textwrap.dedent(
                    """
                    # Status Matrix

                    | Area | Modelled | Coded | Verified | Evidence |
                    |------|----------|-------|----------|----------|
                    | Daily-brief runtime and local HTML output | yes | yes | yes | `apps/agent/delivery/html_report.py`, `scripts/run_daily_brief_fixture.py` |
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text(
                "Implemented today: daily brief path.\nPlanned next: alert scoring, alert delivery, portfolio relevance.\n",
                encoding="utf-8",
            )

            errors = validate_artifacts.validate_repo_artifacts(root)

            self.assertTrue(any("M007" in error and "planned" in error for error in errors), errors)

    def test_readme_requires_alerts_to_be_marked_planned_until_alert_tickets_are_implemented(self):
        backlog = {
            "tickets": [
                {"id": "M006", "status": "planned", "files": ["apps/agent/alerts/scoring.py"]},
                {"id": "M010", "status": "planned", "files": ["apps/agent/delivery/email_sender.py"]},
            ]
        }

        errors = validate_artifacts.validate_readme_status(
            "This repository produces citation-grounded daily briefs and major-event alerts.",
            backlog,
        )

        self.assertEqual(
            errors,
            ["README.md must mark alerts as planned until backlog tickets M006 and M010 are implemented."],
        )

    def test_status_matrix_ticket_rows_must_match_backlog_ticket_status(self):
        backlog = {
            "tickets": [
                {"id": "M010", "status": "planned", "files": ["apps/agent/delivery/email_sender.py"]},
            ]
        }
        status_matrix_text = textwrap.dedent(
            """
            # Status Matrix

            | Area | Modelled | Coded | Verified | Evidence |
            |------|----------|-------|----------|----------|
            | Alert delivery runtime | yes | yes | yes | `artifacts/modelling/backlog.json` (`M010`) |
            """
        )

        errors = validate_artifacts.validate_status_matrix(status_matrix_text, backlog)

        self.assertEqual(
            errors,
            ["docs/status-matrix.md row for ticket M010 must report coded=no and verified=no while backlog status is planned."],
        )

    def test_script_entrypoint_passes_for_repo_state(self):
        repo_root = Path(__file__).resolve().parents[2]
        script_path = repo_root / "scripts" / "validate_artifacts.py"

        completed = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Artifact validation passed.", completed.stdout)


if __name__ == "__main__":
    unittest.main()
