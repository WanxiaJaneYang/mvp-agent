from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_TEST_COMMAND = 'python -m unittest discover -s tests -t . -p "test_*.py" -v'


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

    def test_readme_marks_lint_and_type_checks_as_informational(self):
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("informational today", readme_text)
        self.assertIn("not CI-gated yet", readme_text)
        self.assertIn("currently fail on pre-existing repo-wide issues", readme_text)

    def test_ci_uses_supported_test_command(self):
        ci_text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        self.assertIn(SUPPORTED_TEST_COMMAND, ci_text)


if __name__ == "__main__":
    unittest.main()
