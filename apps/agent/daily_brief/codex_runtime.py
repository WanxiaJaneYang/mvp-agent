from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast

from apps.agent.daily_brief.model_interfaces import ClaimComposerInput, ClaimComposerProvider, IssuePlannerProvider
from apps.agent.daily_brief.openai_claim_composer import OpenAIClaimComposer
from apps.agent.daily_brief.openai_issue_planner import OpenAIIssuePlanner

CODEX_EXECUTABLE = "codex"
CODEX_CLI_REQUIRED_MESSAGE = "Codex runtime requires the `codex` CLI to be installed."
CODEX_LOGIN_REQUIRED_MESSAGE = "Codex runtime requires an active `codex login` session."
CODEX_OUTPUT_WRAPPER_KEY = "result"
DEFAULT_CODEX_TIMEOUT_SECONDS = 300.0

CodexRunner = Callable[..., subprocess.CompletedProcess[str] | Any]
WhichResolver = Callable[[str], str | None]


class CodexExecJsonClient:
    def __init__(
        self,
        *,
        runner: CodexRunner | None = None,
        executable: str = CODEX_EXECUTABLE,
        which_resolver: WhichResolver | None = None,
        timeout_seconds: float = DEFAULT_CODEX_TIMEOUT_SECONDS,
    ) -> None:
        self._runner = runner or subprocess.run
        self._executable = executable
        self._which_resolver = which_resolver or shutil.which
        self._timeout_seconds = timeout_seconds

    def create_json_response(self, request_payload: Mapping[str, Any]) -> str:
        prompt = _build_exec_prompt(request_payload=request_payload)
        output_schema, output_wrapper_key = _build_output_schema(request_payload=request_payload)
        resolved_executable = resolve_codex_executable(
            executable=self._executable,
            which_resolver=self._which_resolver,
        )
        with tempfile.TemporaryDirectory(prefix="codex-runtime-") as temp_dir:
            temp_dir_path = Path(temp_dir)
            schema_path = temp_dir_path / "output-schema.json"
            output_path = temp_dir_path / "output-last-message.json"
            _write_json_file(path=schema_path, payload=output_schema)
            try:
                completed = self._runner(
                    [
                        resolved_executable,
                        "exec",
                        "--output-schema",
                        str(schema_path),
                        "--output-last-message",
                        str(output_path),
                        "-",
                    ],
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
            return _read_output_payload(output_path=output_path, output_wrapper_key=output_wrapper_key)


def build_codex_daily_brief_providers(
    *,
    codex_runner: CodexRunner | None = None,
    cli_checker: Callable[[], bool] | None = None,
    login_checker: Callable[[], bool] | None = None,
    executable: str = CODEX_EXECUTABLE,
    which_resolver: WhichResolver | None = None,
    timeout_seconds: float = DEFAULT_CODEX_TIMEOUT_SECONDS,
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
    if not isinstance(messages, list) or not messages:
        raise ValueError("Codex runtime requires at least one message.")

    prompt_payload = {
        "task": request_payload.get("task"),
        "messages": [dict(message) for message in messages if isinstance(message, Mapping)],
        "input": dict(request_payload.get("input", {})) if isinstance(request_payload.get("input"), Mapping) else {},
    }
    return (
        "Return only valid JSON that matches the attached output schema. "
        "Do not wrap the answer in markdown or commentary.\n\n"
        f"{json.dumps(prompt_payload, indent=2, sort_keys=True)}"
    )


def _build_output_schema(*, request_payload: Mapping[str, Any]) -> tuple[dict[str, Any], str | None]:
    response_format = request_payload.get("response_format")
    if not isinstance(response_format, Mapping):
        raise ValueError("Codex runtime requires response_format.")
    if response_format.get("type") != "json_schema":
        raise ValueError("Codex runtime requires a json_schema response_format.")

    json_schema = response_format.get("json_schema")
    if not isinstance(json_schema, Mapping):
        raise ValueError("Codex runtime requires response_format.json_schema.")

    schema = json_schema.get("schema")
    if not isinstance(schema, Mapping):
        raise ValueError("Codex runtime requires response_format.json_schema.schema.")
    schema_dict = dict(schema)
    if schema_dict.get("type") == "object":
        return schema_dict, None
    return (
        {
            "type": "object",
            "additionalProperties": False,
            "required": [CODEX_OUTPUT_WRAPPER_KEY],
            "properties": {CODEX_OUTPUT_WRAPPER_KEY: schema_dict},
        },
        CODEX_OUTPUT_WRAPPER_KEY,
    )


def _write_json_file(*, path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True), encoding="utf-8")


def _read_output_payload(*, output_path: Path, output_wrapper_key: str | None) -> str:
    if not output_path.exists():
        raise ValueError("Codex exec did not return output.")
    payload = output_path.read_text(encoding="utf-8").strip()
    if not payload:
        raise ValueError("Codex exec did not return output.")
    if output_wrapper_key is None:
        return payload

    parsed_payload = json.loads(payload)
    if not isinstance(parsed_payload, Mapping) or output_wrapper_key not in parsed_payload:
        raise ValueError("Codex exec did not return output.")
    return json.dumps(parsed_payload[output_wrapper_key], separators=(",", ":"))
