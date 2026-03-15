from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tools.repo_dashboard.app import create_app


class RepoDashboardFrontendTests(unittest.TestCase):
    def test_root_serves_dashboard_shell_with_operator_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()
            app = create_app(repo_root=repo_root, data_dir=repo_root / "tools" / "repo_dashboard" / "data")
            client = TestClient(app)

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertIn('id="architecture-panel"', response.text)
            self.assertIn('id="health-panel"', response.text)
            self.assertIn('id="control-panel"', response.text)
            self.assertIn('id="runtime-panel"', response.text)
            self.assertIn('id="log-viewer"', response.text)
            self.assertIn('/static/app.js', response.text)
            self.assertIn('/static/styles.css', response.text)

    def test_static_assets_are_mounted_and_served(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()
            app = create_app(repo_root=repo_root, data_dir=repo_root / "tools" / "repo_dashboard" / "data")
            client = TestClient(app)

            script = client.get("/static/app.js")
            styles = client.get("/static/styles.css")

            self.assertEqual(script.status_code, 200)
            self.assertIn("renderArchitecture", script.text)
            self.assertEqual(styles.status_code, 200)
            self.assertIn(".dashboard-shell", styles.text)


if __name__ == "__main__":
    unittest.main()
