from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tools.repo_dashboard.app import create_app


class FakeCommandRunner:
    def __init__(self) -> None:
        self.started_kinds: list[str] = []
        self.logs = {"run_id": None, "lines": [], "is_running": False, "log_path": None}
        self.raise_busy = False

    def start_run(self, run_kind: str) -> dict[str, object]:
        if self.raise_busy:
            raise RuntimeError("A dashboard run is already active.")
        self.started_kinds.append(run_kind)
        run_id = f"{run_kind}_001"
        self.logs = {
            "run_id": run_id,
            "lines": ["starting", "done"],
            "is_running": True,
            "log_path": f"C:/logs/{run_id}.log",
        }
        return {
            "run_id": run_id,
            "run_kind": run_kind,
            "status": "running",
            "command": ["python", "demo.py"],
            "started_at_utc": "2026-03-15T10:00:00Z",
            "finished_at_utc": None,
            "exit_code": None,
            "log_path": self.logs["log_path"],
            "base_dir": ".tmp_repo_dashboard/demo",
            "artifact_paths": {},
            "publish_decision": None,
            "reason": None,
            "reason_codes": [],
            "summary": None,
        }

    def latest_logs(self) -> dict[str, object]:
        return dict(self.logs)

    def refresh_active_run(self) -> None:
        return None


class RepoDashboardApiTests(unittest.TestCase):
    def _build_repo_fixture(self, repo_root: Path) -> None:
        (repo_root / "artifacts" / "modelling").mkdir(parents=True)
        (repo_root / "artifacts" / "modelling" / "pipeline.md").write_text("# pipeline", encoding="utf-8")
        (repo_root / "artifacts" / "modelling" / "data_model.md").write_text("# data", encoding="utf-8")
        (repo_root / "artifacts" / "modelling" / "decision_record_schema.md").write_text("# schema", encoding="utf-8")

        decision_record = repo_root / ".tmp_repo_dashboard" / "demo" / "artifacts" / "decision_records" / "2026-03-15" / "run_daily_fixture.json"
        decision_record.parent.mkdir(parents=True, exist_ok=True)
        decision_record.write_text(
            json.dumps(
                {
                    "publish_decision": "hold",
                    "reason_codes": ["citation_validation_abstained"],
                    "decision_rationale": {"summary": "Validation abstained"},
                }
            ),
            encoding="utf-8",
        )

    def test_get_endpoints_return_dashboard_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()
            self._build_repo_fixture(repo_root)
            data_dir = repo_root / "tools" / "repo_dashboard" / "data"
            runner = FakeCommandRunner()
            app = create_app(repo_root=repo_root, data_dir=data_dir, command_runner=runner)
            client = TestClient(app)

            overview = client.get("/api/overview")
            health = client.get("/api/health")
            latest_run = client.get("/api/latest-run")
            artifacts = client.get("/api/artifacts")

            self.assertEqual(overview.status_code, 200)
            self.assertEqual(health.status_code, 200)
            self.assertEqual(latest_run.status_code, 200)
            self.assertEqual(artifacts.status_code, 200)
            self.assertEqual(overview.json()["repo_name"], "repo")
            self.assertEqual(health.json()["fixture"]["publish_decision"], "hold")
            self.assertEqual(latest_run.json()["publish_decision"], "hold")
            self.assertEqual(artifacts.json()["latest"]["reason"], "Validation abstained")

    def test_run_endpoints_start_named_commands_and_block_when_busy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()
            self._build_repo_fixture(repo_root)
            data_dir = repo_root / "tools" / "repo_dashboard" / "data"
            runner = FakeCommandRunner()
            app = create_app(repo_root=repo_root, data_dir=data_dir, command_runner=runner)
            client = TestClient(app)

            response = client.post("/api/run/fixture")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["run_kind"], "fixture")
            self.assertEqual(runner.started_kinds, ["fixture"])

            runner.raise_busy = True
            busy = client.post("/api/run/live")
            self.assertEqual(busy.status_code, 409)
            self.assertIn("already active", busy.json()["detail"])

    def test_latest_logs_endpoint_returns_runner_log_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()
            self._build_repo_fixture(repo_root)
            data_dir = repo_root / "tools" / "repo_dashboard" / "data"
            runner = FakeCommandRunner()
            app = create_app(repo_root=repo_root, data_dir=data_dir, command_runner=runner)
            client = TestClient(app)

            client.post("/api/run/evals")
            logs = client.get("/api/logs/latest")

            self.assertEqual(logs.status_code, 200)
            self.assertEqual(logs.json()["run_id"], "evals_001")
            self.assertEqual(logs.json()["lines"], ["starting", "done"])
            self.assertTrue(logs.json()["is_running"])

    def test_refresh_endpoint_rebuilds_overview(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()
            self._build_repo_fixture(repo_root)
            data_dir = repo_root / "tools" / "repo_dashboard" / "data"
            runner = FakeCommandRunner()
            app = create_app(repo_root=repo_root, data_dir=data_dir, command_runner=runner)
            client = TestClient(app)

            response = client.post("/api/refresh")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["overview"]["repo_name"], "repo")
            self.assertEqual(len(response.json()["overview"]["diagram_cards"]), 3)


if __name__ == "__main__":
    unittest.main()
