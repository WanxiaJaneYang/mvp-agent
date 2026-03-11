from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Mapping
from json import JSONDecodeError
from pathlib import Path
from typing import Any, cast

from apps.agent.daily_brief.model_interfaces import ClaimComposerInput, ClaimComposerProvider, IssuePlannerProvider
from apps.agent.daily_brief.openai_claim_composer import OpenAIClaimComposer
from apps.agent.daily_brief.openai_issue_planner import OpenAIIssuePlanner

CODEX_EXECUTABLE = "codex"
CODEX_CLI_REQUIRED_MESSAGE = "Codex runtime requires the `codex` CLI to be installed."
CODEX_LOGIN_REQUIRED_MESSAGE = "Codex runtime requires an active `codex login` session."

CodexRunner = Callable[..., subprocess.CompletedProcess[str] | Any]
WhichResolver = Callable[[str], str | None]


class CodexExecJsonClient:
    def __init__(
        self,
        *,
        runner: CodexRunner | None = None,
        executable: str = CODEX_EXECUTABLE,
        which_resolver: WhichResolver | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._runner = runner or subprocess.run
        self._executable = executable
        self._which_resolver = which_resolver or shutil.which
        self._timeout_seconds = timeout_seconds

    def create_json_response(self, request_payload: Mapping[str, Any]) -> str:
        prompt = _build_exec_prompt(request_payload=request_payload)
        resolved_executable = resolve_codex_executable(
            executable=self._executable,
            which_resolver=self._which_resolver,
        )
        try:
            completed = self._runner(
                [resolved_executable, "exec", "--json", "-"],
                capture_output=True,
                text=True,
                input=prompt,
                timeout=self._timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ValueError(CODEX_CLI_REQUIRED_MESSAGE) from exc
        if int(getattr(completed, "returncode", 1)) != 0:
            error_text = str(getattr(completed, "stderr", "") or getattr(completed, "stdout", "")).strip()
            raise ValueError(error_text or "Codex exec failed.")

        stdout = str(getattr(completed, "stdout", "")).strip()
        if not stdout:
            raise ValueError("Codex exec did not return output.")
        return _extract_last_message(stdout)


def build_codex_daily_brief_providers(
    *,
    codex_runner: CodexRunner | None = None,
    cli_checker: Callable[[], bool] | None = None,
    login_checker: Callable[[], bool] | None = None,
    executable: str = CODEX_EXECUTABLE,
    which_resolver: WhichResolver | None = None,
    timeout_seconds: float = 60.0,
) -> tuple[IssuePlannerProvider, ClaimComposerProvider]:
    resolved_runner = codex_runner or subprocess.run
    resolved_which_resolver = which_resolver or shutil.which
    resolved_cli_checker = cli_checker or (
        lambda: _codex_cli_available(
            runner=resolved_runner,
            executable=executable,
            which_resolver=resolved_which_resolver,
        )
    )
    resolved_login_checker = login_checker or (
        lambda: _codex_login_available(
            runner=resolved_runner,
            executable=executable,
            which_resolver=resolved_which_resolver,
        )
    )
    if not resolved_cli_checker():
        raise ValueError(CODEX_CLI_REQUIRED_MESSAGE)
    if not resolved_login_checker():
        raise ValueError(CODEX_LOGIN_REQUIRED_MESSAGE)

    runtime_client = CodexExecJsonClient(
        runner=resolved_runner,
        executable=executable,
        which_resolver=resolved_which_resolver,
        timeout_seconds=timeout_seconds,
    )
    response_loader = runtime_client.create_json_response
    return (
        OpenAIIssuePlanner(response_loader=response_loader),
        OpenAIClaimComposer(
            response_loader=cast(
                Callable[[ClaimComposerInput], str | list[dict[str, Any]]],
                response_loader,
            )
        ),
    )


def resolve_codex_executable(*, executable: str, which_resolver: WhichResolver | None = None) -> str:
    candidate_path = Path(executable)
    if candidate_path.is_absolute() or candidate_path.parent != Path("."):
        return str(candidate_path)

    resolved = (which_resolver or shutil.which)(executable)
    if resolved:
        return resolved
    return executable


def _codex_cli_available(*, runner: CodexRunner, executable: str, which_resolver: WhichResolver) -> bool:
    resolved_executable = resolve_codex_executable(executable=executable, which_resolver=which_resolver)
    try:
        completed = runner(
            [resolved_executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10.0,
            check=False,
        )
    except FileNotFoundError:
        return False
    return int(getattr(completed, "returncode", 1)) == 0


def _codex_login_available(*, runner: CodexRunner, executable: str, which_resolver: WhichResolver) -> bool:
    resolved_executable = resolve_codex_executable(executable=executable, which_resolver=which_resolver)
    try:
        completed = runner(
            [resolved_executable, "login", "status"],
            capture_output=True,
            text=True,
            timeout=10.0,
            check=False,
        )
    except FileNotFoundError:
        return False
    return int(getattr(completed, "returncode", 1)) == 0


def _build_exec_prompt(*, request_payload: Mapping[str, Any]) -> str:
    messages = request_payload.get("messages")
    response_format = request_payload.get("response_format")
    if not isinstance(messages, list) or not messages:
        raise ValueError("Codex runtime requires at least one message.")
    if not isinstance(response_format, Mapping):
        raise ValueError("Codex runtime requires response_format.")

    prompt_payload = {
        "task": request_payload.get("task"),
        "messages": [dict(message) for message in messages if isinstance(message, Mapping)],
        "response_format": dict(response_format),
        "input": dict(request_payload.get("input", {})) if isinstance(request_payload.get("input"), Mapping) else {},
    }
    return (
        "Return only valid JSON that matches the provided response_format. "
        "Do not wrap the answer in markdown or commentary.\n\n"
        f"{json.dumps(prompt_payload, indent=2, sort_keys=True)}"
    )


def _extract_last_message(stdout: str) -> str:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if len(lines) > 1:
        for line in reversed(lines):
            try:
                parsed_line = json.loads(line)
            except JSONDecodeError:
                continue
            if isinstance(parsed_line, Mapping) and parsed_line.get("type") == "item.completed":
                item = parsed_line.get("item")
                if isinstance(item, Mapping) and item.get("type") == "agent_message":
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        return text.strip()

    try:
        parsed = json.loads(stdout)
    except JSONDecodeError:
        return stdout.strip()

    if isinstance(parsed, Mapping):
        for key in ("output_text", "last_message", "content", "message"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return stdout.strip()

    if isinstance(parsed, list):
        for item in reversed(parsed):
            if not isinstance(item, Mapping):
                continue
            for key in ("output_text", "last_message", "content", "message"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return stdout.strip()

    return stdout.strip()
