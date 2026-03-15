import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_TEST_COMMAND = 'python -m unittest discover -s tests -t . -p "test_*.py" -v'
SUPPORTED_RUFF_COMMAND = "python -m ruff check apps tests scripts tools"
SUPPORTED_MYPY_COMMAND = "python -m mypy apps tools"
SUPPORTED_COMPILE_COMMAND = "python -m compileall -q apps tests scripts tools"
SUPPORTED_DASHBOARD_COMMAND = "python -m tools.repo_dashboard.app"


class ProjectToolingTests(unittest.TestCase):
    def test_pyproject_declares_supported_python_project(self):
        pyproject_path = ROOT / "pyproject.toml"

        self.assertTrue(pyproject_path.exists(), "pyproject.toml should exist")

        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = pyproject.get("project", {})

        self.assertEqual(project.get("name"), "mvp-agent")
        self.assertEqual(project.get("requires-python"), ">=3.11")

    def test_suite_package_markers_exist_for_nested_discovery(self):
        self.assertTrue((ROOT / "tests" / "agent" / "daily_brief" / "__init__.py").exists())
        self.assertTrue((ROOT / "tests" / "agent" / "delivery" / "__init__.py").exists())

    def test_readme_documents_supported_test_command(self):
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(SUPPORTED_TEST_COMMAND, readme_text)

    def test_readme_documents_gated_lint_and_type_checks(self):
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(SUPPORTED_RUFF_COMMAND, readme_text)
        self.assertIn(SUPPORTED_MYPY_COMMAND, readme_text)
        self.assertIn("required and CI-gated", readme_text)
        self.assertNotIn("informational today", readme_text)
        self.assertNotIn("not CI-gated yet", readme_text)
        self.assertNotIn("currently fail on pre-existing repo-wide issues", readme_text)

    def test_readme_documents_dashboard_launch_command(self):
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(SUPPORTED_DASHBOARD_COMMAND, readme_text)

    def test_dashboard_readme_documents_one_command_launch(self):
        dashboard_readme = (ROOT / "tools" / "repo_dashboard" / "README.md").read_text(encoding="utf-8")

        self.assertIn(SUPPORTED_DASHBOARD_COMMAND, dashboard_readme)
        self.assertIn("http://127.0.0.1:8000/", dashboard_readme)

    def test_ci_uses_supported_commands(self):
        ci_text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        self.assertIn(SUPPORTED_TEST_COMMAND, ci_text)
        self.assertIn(SUPPORTED_RUFF_COMMAND, ci_text)
        self.assertIn(SUPPORTED_MYPY_COMMAND, ci_text)
        self.assertIn(SUPPORTED_COMPILE_COMMAND, ci_text)


if __name__ == "__main__":
    unittest.main()
