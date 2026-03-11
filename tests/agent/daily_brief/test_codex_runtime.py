from __future__ import annotations

import unittest
from types import SimpleNamespace

from apps.agent.daily_brief.openai_claim_composer import OpenAIClaimComposer
from apps.agent.daily_brief.openai_issue_planner import OpenAIIssuePlanner
from apps.agent.daily_brief.codex_runtime import (
    CODEX_LOGIN_REQUIRED_MESSAGE,
    CODEX_CLI_REQUIRED_MESSAGE,
    CodexExecJsonClient,
    build_codex_daily_brief_providers,
)


class CodexRuntimeTests(unittest.TestCase):
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
            return SimpleNamespace(returncode=0, stdout='[{"issue_id":"issue_001"}]\n', stderr="")

        runtime = CodexExecJsonClient(runner=_runner, timeout_seconds=12.5)

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
        self.assertEqual(captured["command"][:4], ["codex", "exec", "--json", "--output-last-message"])
        self.assertIn("daily_brief_issue_planner", captured["command"][4])
        self.assertIn("json_schema", captured["command"][4])
        self.assertEqual(captured["kwargs"]["timeout"], 12.5)
        self.assertTrue(captured["kwargs"]["text"])
        self.assertTrue(captured["kwargs"]["capture_output"])

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
                    "response_format": {"type": "json_schema", "json_schema": {"name": "issue_map_list", "schema": {"type": "array"}}},
                    "messages": [{"role": "user", "content": "Plan issues."}],
                    "input": {"evidence_pack": []},
                }
            )


if __name__ == "__main__":
    unittest.main()
