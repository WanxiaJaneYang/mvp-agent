from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from apps.agent.daily_brief.codex_runtime import (
    CODEX_CLI_REQUIRED_MESSAGE,
    CODEX_LOGIN_REQUIRED_MESSAGE,
    CodexExecJsonClient,
    build_codex_daily_brief_providers,
    resolve_codex_executable,
)
from apps.agent.daily_brief.openai_claim_composer import OpenAIClaimComposer
from apps.agent.daily_brief.openai_issue_planner import OpenAIIssuePlanner


class CodexRuntimeTests(unittest.TestCase):
    def test_resolve_codex_executable_prefers_discovered_windows_launcher_path(self) -> None:
        resolved = resolve_codex_executable(
            executable="codex",
            which_resolver=lambda name: r"C:\Users\Lenovo\AppData\Roaming\npm\codex.cmd" if name == "codex" else None,
        )

        self.assertEqual(resolved, r"C:\Users\Lenovo\AppData\Roaming\npm\codex.cmd")

    def test_build_codex_daily_brief_providers_requires_codex_cli(self) -> None:
        with self.assertRaisesRegex(ValueError, CODEX_CLI_REQUIRED_MESSAGE):
            build_codex_daily_brief_providers(
                cli_checker=lambda: False,
                login_checker=lambda: True,
                codex_runner=lambda *_args, **_kwargs: None,
            )

    def test_build_codex_daily_brief_providers_requires_logged_in_codex(self) -> None:
        with self.assertRaisesRegex(ValueError, CODEX_LOGIN_REQUIRED_MESSAGE):
            build_codex_daily_brief_providers(
                cli_checker=lambda: True,
                login_checker=lambda: False,
                codex_runner=lambda *_args, **_kwargs: None,
            )

    def test_build_codex_daily_brief_providers_returns_issue_planner_and_claim_composer(self) -> None:
        planner, composer = build_codex_daily_brief_providers(
            cli_checker=lambda: True,
            login_checker=lambda: True,
            codex_runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="[]", stderr=""),
        )

        self.assertIsInstance(planner, OpenAIIssuePlanner)
        self.assertIsInstance(composer, OpenAIClaimComposer)

    def test_codex_exec_runtime_returns_last_message_json(self) -> None:
        captured: dict[str, object] = {}

        def _runner(command, **kwargs):
            captured["command"] = command
            captured["kwargs"] = kwargs
            schema_path = Path(command[3])
            output_path = Path(command[5])
            captured["schema"] = json.loads(schema_path.read_text(encoding="utf-8"))
            output_path.write_text('{"result":[{"issue_id":"issue_001"}]}', encoding="utf-8")
            return SimpleNamespace(
                returncode=0,
                stdout="planner completed",
                stderr="",
            )

        runtime = CodexExecJsonClient(
            runner=_runner,
            timeout_seconds=12.5,
            which_resolver=lambda _name: r"C:\Users\Lenovo\AppData\Roaming\npm\codex.cmd",
        )

        payload = runtime.create_json_response(
            {
                "task": "daily_brief_issue_planner",
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "issue_map_list",
                        "strict": True,
                        "schema": {"type": "array"},
                    },
                },
                "messages": [
                    {"role": "system", "content": "Return strict JSON only."},
                    {"role": "user", "content": "Plan issues."},
                ],
                "input": {
                    "run_id": "run_001",
                    "generated_at_utc": "2026-03-12T10:00:00Z",
                    "evidence_pack": [{"chunk_id": "chunk_001", "text": "Growth cools."}],
                },
            }
        )

        self.assertEqual(payload, '[{"issue_id":"issue_001"}]')
        self.assertEqual(
            captured["command"][:7],
            [
                r"C:\Users\Lenovo\AppData\Roaming\npm\codex.cmd",
                "exec",
                "--output-schema",
                captured["command"][3],
                "--output-last-message",
                captured["command"][5],
                "-",
            ],
        )
        self.assertIn("daily_brief_issue_planner", captured["kwargs"]["input"])
        self.assertNotIn("json_schema", captured["kwargs"]["input"])
        self.assertEqual(
            captured["schema"],
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["result"],
                "properties": {"result": {"type": "array"}},
            },
        )
        self.assertEqual(captured["kwargs"]["timeout"], 12.5)
        self.assertTrue(captured["kwargs"]["text"])
        self.assertTrue(captured["kwargs"]["capture_output"])

    def test_codex_exec_runtime_rejects_missing_output_file(self) -> None:
        runtime = CodexExecJsonClient(
            runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="planner completed", stderr=""),
            which_resolver=lambda _name: r"C:\Users\Lenovo\AppData\Roaming\npm\codex.cmd",
        )

        with self.assertRaisesRegex(ValueError, "Codex exec did not return output."):
            runtime.create_json_response(
                {
                    "task": "daily_brief_issue_planner",
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {"name": "issue_map_list", "schema": {"type": "array"}},
                    },
                    "messages": [{"role": "user", "content": "Plan issues."}],
                    "input": {"evidence_pack": []},
                }
            )

    def test_codex_exec_runtime_uses_extended_default_timeout(self) -> None:
        captured: dict[str, object] = {}

        def _runner(command, **kwargs):
            captured["command"] = command
            captured["timeout"] = kwargs["timeout"]
            Path(command[5]).write_text('{"result":[{"issue_id":"issue_001"}]}', encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="planner completed", stderr="")

        runtime = CodexExecJsonClient(
            runner=_runner,
            which_resolver=lambda _name: r"C:\Users\Lenovo\AppData\Roaming\npm\codex.cmd",
        )

        payload = runtime.create_json_response(
            {
                "task": "daily_brief_issue_planner",
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "issue_map_list", "schema": {"type": "array"}},
                },
                "messages": [{"role": "user", "content": "Plan issues."}],
                "input": {"evidence_pack": []},
            }
        )

        self.assertEqual(payload, '[{"issue_id":"issue_001"}]')
        self.assertEqual(captured["timeout"], 300.0)

    def test_codex_exec_runtime_raises_provider_specific_error_on_file_not_found(self) -> None:
        runtime = CodexExecJsonClient(
            runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError("codex")),
            which_resolver=lambda _name: None,
        )

        with self.assertRaisesRegex(ValueError, CODEX_CLI_REQUIRED_MESSAGE):
            runtime.create_json_response(
                {
                    "task": "daily_brief_issue_planner",
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {"name": "issue_map_list", "schema": {"type": "array"}},
                    },
                    "messages": [{"role": "user", "content": "Plan issues."}],
                    "input": {"evidence_pack": []},
                }
            )

    def test_codex_exec_runtime_rejects_failed_command(self) -> None:
        runtime = CodexExecJsonClient(
            runner=lambda *_args, **_kwargs: SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="not logged in",
            )
        )

        with self.assertRaisesRegex(ValueError, "not logged in"):
            runtime.create_json_response(
                {
                    "task": "daily_brief_issue_planner",
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {"name": "issue_map_list", "schema": {"type": "array"}},
                    },
                    "messages": [{"role": "user", "content": "Plan issues."}],
                    "input": {"evidence_pack": []},
                }
            )


if __name__ == "__main__":
    unittest.main()
