import argparse
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TRELLIS_SCRIPTS = Path(__file__).resolve().parents[2] / ".trellis" / "scripts"
if str(TRELLIS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TRELLIS_SCRIPTS))


def _load_task_module():
    return importlib.import_module("task")


def _load_cli_adapter():
    return importlib.import_module("common.cli_adapter").CLIAdapter


def _load_get_worktree_base_dir():
    return importlib.import_module("common.worktree").get_worktree_base_dir


class TaskScriptTests(unittest.TestCase):
    def test_cmd_create_fails_when_task_directory_exists(self):
        task = _load_task_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            task_dir = repo_root / ".trellis" / "tasks" / "03-10-existing-task"
            task_dir.mkdir(parents=True)
            task_json = task_dir / "task.json"
            original = {"status": "in_progress", "branch": "feature/existing"}
            task_json.write_text(json.dumps(original), encoding="utf-8")

            args = argparse.Namespace(
                title="Existing Task",
                assignee=None,
                slug="existing-task",
                priority="P2",
                description=None,
                parent=None,
            )

            with (
                patch.object(task, "get_repo_root", return_value=repo_root),
                patch.object(task, "get_developer", return_value="tester"),
                patch.object(task, "generate_task_date_prefix", return_value="03-10"),
            ):
                rc = task.cmd_create(args)

            self.assertEqual(rc, 1)
            self.assertEqual(
                json.loads(task_json.read_text(encoding="utf-8")),
                original,
            )

    def test_current_task_match_requires_exact_directory_name(self):
        task = _load_task_module()

        self.assertTrue(
            task._current_task_matches_dir_name(
                ".trellis/tasks/03-10-sync-trellis",
                "03-10-sync-trellis",
            )
        )
        self.assertFalse(
            task._current_task_matches_dir_name(
                ".trellis/tasks/03-10-sync-trellis-extra",
                "03-10-sync-trellis",
            )
        )


class CLIAdapterTests(unittest.TestCase):
    def test_cursor_platform_fails_fast_for_run_command(self):
        CLIAdapter = _load_cli_adapter()
        adapter = CLIAdapter("cursor")

        with self.assertRaises(ValueError):
            adapter.build_run_command(agent="plan", prompt="hello")


class WorktreeConfigTests(unittest.TestCase):
    def test_non_absolute_worktree_dir_is_repo_relative(self):
        get_worktree_base_dir = _load_get_worktree_base_dir()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            config_dir = repo_root / ".trellis"
            config_dir.mkdir(parents=True)
            (config_dir / "worktree.yaml").write_text(
                "worktree_dir: .worktrees\n",
                encoding="utf-8",
            )

            self.assertEqual(
                get_worktree_base_dir(repo_root),
                repo_root / ".worktrees",
            )


if __name__ == "__main__":
    unittest.main()
