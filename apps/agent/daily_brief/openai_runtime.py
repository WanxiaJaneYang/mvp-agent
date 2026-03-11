from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from typing import Any, cast

from apps.agent.daily_brief.model_interfaces import (
    ClaimComposerInput,
    ClaimComposerProvider,
    IssuePlannerProvider,
)
from apps.agent.daily_brief.openai_claim_composer import OpenAIClaimComposer
from apps.agent.daily_brief.openai_issue_planner import OpenAIIssuePlanner

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_BASE_URL_ENV = "OPENAI_BASE_URL"
OPENAI_ORGANIZATION_ENV = "OPENAI_ORGANIZATION"
OPENAI_PROJECT_ENV = "OPENAI_PROJECT"


class OpenAIResponsesTextClient:
    def __init__(self, *, client: Any, model: str) -> None:
        self._client = client
        self._model = model

    def create_json_response(self, request_payload: Mapping[str, Any]) -> str | list[dict[str, Any]]:
        system_message, input_messages = _split_messages(request_payload=request_payload)
        text_format, array_wrapper_key = _build_text_format(request_payload=request_payload)
        response = self._client.responses.create(
            model=self._model,
            instructions=system_message,
            input=input_messages,
            text={"format": text_format},
        )
        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise ValueError("OpenAI response did not include output_text.")
        if array_wrapper_key is None:
            return output_text
        parsed_output = json.loads(output_text)
        if not isinstance(parsed_output, Mapping):
            raise ValueError("OpenAI response did not match wrapped schema.")
        items = parsed_output.get(array_wrapper_key)
        if not isinstance(items, list):
            raise ValueError("OpenAI response did not include wrapped items.")
        return [dict(item) for item in items if isinstance(item, Mapping)]


def build_openai_daily_brief_providers(
    *,
    api_key: str | None = None,
    model: str = DEFAULT_OPENAI_MODEL,
    base_url: str | None = None,
    organization: str | None = None,
    project: str | None = None,
    timeout_seconds: float = 60.0,
    client_factory: Callable[..., Any] | None = None,
) -> tuple[IssuePlannerProvider, ClaimComposerProvider]:
    resolved_api_key = api_key or os.environ.get(OPENAI_API_KEY_ENV)
    if not resolved_api_key:
        raise ValueError(f"OpenAI provider requires {OPENAI_API_KEY_ENV}.")

    resolved_client_factory = client_factory or _load_openai_client_factory()
    client_kwargs: dict[str, Any] = {
        "api_key": resolved_api_key,
        "timeout": timeout_seconds,
    }
    resolved_base_url = base_url or os.environ.get(OPENAI_BASE_URL_ENV)
    resolved_organization = organization or os.environ.get(OPENAI_ORGANIZATION_ENV)
    resolved_project = project or os.environ.get(OPENAI_PROJECT_ENV)
    if resolved_base_url:
        client_kwargs["base_url"] = resolved_base_url
    if resolved_organization:
        client_kwargs["organization"] = resolved_organization
    if resolved_project:
        client_kwargs["project"] = resolved_project

    runtime_client = OpenAIResponsesTextClient(
        client=resolved_client_factory(**client_kwargs),
        model=model,
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


def _load_openai_client_factory() -> Callable[..., Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ValueError("OpenAI runtime requires the `openai` package to be installed.") from exc
    return OpenAI


def _split_messages(*, request_payload: Mapping[str, Any]) -> tuple[str | None, list[dict[str, str]]]:
    raw_messages = request_payload.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ValueError("OpenAI request payload requires at least one message.")

    instructions: str | None = None
    input_messages: list[dict[str, str]] = []
    for index, item in enumerate(raw_messages):
        if not isinstance(item, Mapping):
            raise ValueError("OpenAI request payload contains an invalid message.")
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        if not role or not content:
            raise ValueError("OpenAI request payload contains an invalid message.")
        if index == 0 and role == "system":
            instructions = content
            continue
        input_messages.append({"role": role, "content": content})
    if not input_messages:
        raise ValueError("OpenAI request payload requires at least one non-system message.")
    return instructions, input_messages


def _build_text_format(*, request_payload: Mapping[str, Any]) -> tuple[dict[str, Any], str | None]:
    response_format = request_payload.get("response_format")
    if not isinstance(response_format, Mapping):
        raise ValueError("OpenAI request payload requires response_format.")
    if response_format.get("type") != "json_schema":
        raise ValueError("OpenAI request payload requires a json_schema response_format.")
    json_schema = response_format.get("json_schema")
    if not isinstance(json_schema, Mapping):
        raise ValueError("OpenAI request payload requires json_schema details.")
    name = str(json_schema.get("name") or "").strip()
    schema = json_schema.get("schema")
    if not name or not isinstance(schema, Mapping):
        raise ValueError("OpenAI request payload requires a named schema.")
    wrapped_schema, array_wrapper_key = _wrap_array_schema(schema=dict(schema))
    return ({
        "type": "json_schema",
        "name": name,
        "schema": wrapped_schema,
        "strict": bool(json_schema.get("strict", False)),
    }, array_wrapper_key)


def _wrap_array_schema(*, schema: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    if schema.get("type") != "array":
        return schema, None
    return (
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["items"],
            "properties": {
                "items": schema,
            },
        },
        "items",
    )
