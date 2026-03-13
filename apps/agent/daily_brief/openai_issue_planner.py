from __future__ import annotations

import json
from collections.abc import Callable
from json import JSONDecodeError
from typing import Any, cast

from apps.agent.daily_brief.model_interfaces import IssuePlannerInput, IssuePlannerProvider
from apps.agent.pipeline.types import IssueMap

MAX_EVIDENCE_PACK_ITEMS = 12
MAX_EVIDENCE_TEXT_CHARS = 280
MAX_PRIOR_CONTEXT_TEXT_CHARS = 240
REQUEST_TASK = "daily_brief_issue_planner"
ISSUE_PLAN_PROMPT_TEMPLATE = (
    "You are planning up to {issue_budget} issue-centered literature review topic(s) "
    "for a daily brief. Use only the provided evidence pack. Return strict JSON matching "
    "the issue map schema."
)


class OpenAIIssuePlanner(IssuePlannerProvider):
    def __init__(self, *, response_loader: Callable[[dict[str, Any]], Any] | None) -> None:
        self._response_loader = response_loader

    def plan_issues(self, *, brief_input: IssuePlannerInput) -> list[IssueMap]:
        if self._response_loader is None:
            raise ValueError("OpenAIIssuePlanner requires a response_loader for this local runtime slice.")
        request_payload = _build_request_payload(brief_input)
        payload = self._response_loader(request_payload)
        parsed = _parse_response_payload(payload)
        if not isinstance(parsed, list) or len(parsed) == 0:
            raise ValueError("Issue planner output must be a non-empty list.")

        issues: list[IssueMap] = []
        required_fields = set(IssueMap.__annotations__)
        seen_issue_ids: set[str] = set()
        valid_evidence_ids = _extract_evidence_ids(brief_input)
        for item in parsed:
            if not isinstance(item, dict) or set(item) != required_fields:
                raise ValueError("Malformed issue planner output.")
            validated = _validate_issue_map(item, valid_evidence_ids=valid_evidence_ids)
            if validated["issue_id"] in seen_issue_ids:
                raise ValueError("Malformed issue planner output.")
            seen_issue_ids.add(validated["issue_id"])
            issues.append(validated)
        return issues


def _build_request_payload(brief_input: IssuePlannerInput) -> dict[str, Any]:
    issue_budget = _issue_budget(brief_input)
    bounded_input = {
        "run_id": brief_input["run_id"],
        "generated_at_utc": brief_input["generated_at_utc"],
        "brief_plan": dict(brief_input["brief_plan"]),
        "evidence_pack": [
            _normalize_evidence_item(item)
            for item in brief_input["evidence_pack"][:MAX_EVIDENCE_PACK_ITEMS]
        ],
        "prior_brief_context": _normalize_prior_brief_context(brief_input.get("prior_brief_context")),
    }
    return {
        "task": REQUEST_TASK,
        "run_id": brief_input["run_id"],
        "generated_at_utc": brief_input["generated_at_utc"],
        "response_format": {
            "type": "json_schema",
            "json_schema": _issue_map_json_schema(issue_budget=issue_budget),
        },
        "messages": [
            {
                "role": "system",
                "content": ISSUE_PLAN_PROMPT_TEMPLATE.format(issue_budget=issue_budget),
            },
            {
                "role": "user",
                "content": (
                    f"Plan up to {issue_budget} issue-centered daily brief topic(s) from the bounded "
                    "evidence pack. Return only strict JSON matching the provided schema."
                ),
            },
        ],
        "input": bounded_input,
    }


def _issue_map_json_schema(*, issue_budget: int) -> dict[str, Any]:
    return {
        "name": "issue_map_list",
        "strict": True,
        "schema": {
            "type": "array",
            "minItems": 1,
            "maxItems": issue_budget,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "issue_id",
                    "issue_question",
                    "thesis_hint",
                    "supporting_evidence_ids",
                    "opposing_evidence_ids",
                    "minority_evidence_ids",
                    "watch_evidence_ids",
                ],
                "properties": {
                    "issue_id": {"type": "string"},
                    "issue_question": {"type": "string"},
                    "thesis_hint": {"type": "string"},
                    "supporting_evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "opposing_evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "minority_evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "watch_evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    }


def _issue_budget(brief_input: IssuePlannerInput) -> int:
    raw_budget = brief_input["brief_plan"].get("issue_budget", 1)
    try:
        return max(1, int(raw_budget))
    except (TypeError, ValueError):
        return 1


def _normalize_evidence_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field in ("chunk_id", "doc_id", "publisher", "title", "retrieval_score"):
        if field in item:
            normalized[field] = item[field]
    normalized["text"] = _truncate_text(item.get("text"))
    return normalized


def _normalize_prior_brief_context(prior_brief_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if prior_brief_context is None:
        return None

    normalized: dict[str, Any] = {}
    for key, value in prior_brief_context.items():
        if isinstance(value, str):
            normalized[key] = _truncate_text(value, limit=MAX_PRIOR_CONTEXT_TEXT_CHARS)
        elif isinstance(value, list):
            bounded_list: list[Any] = []
            for item in value[:5]:
                if isinstance(item, str):
                    bounded_list.append(_truncate_text(item, limit=MAX_PRIOR_CONTEXT_TEXT_CHARS))
                else:
                    bounded_list.append(item)
            normalized[key] = bounded_list
        else:
            normalized[key] = value
    return normalized


def _truncate_text(value: Any, *, limit: int = MAX_EVIDENCE_TEXT_CHARS) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _parse_response_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except JSONDecodeError as exc:
            raise ValueError("Malformed issue planner output.") from exc
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("parsed"), list):
            return payload["parsed"]
        if isinstance(payload.get("output_text"), str):
            try:
                return json.loads(payload["output_text"])
            except JSONDecodeError as exc:
                raise ValueError("Malformed issue planner output.") from exc
    raise ValueError("Malformed issue planner output.")


def _extract_evidence_ids(brief_input: IssuePlannerInput) -> set[str]:
    evidence_ids: set[str] = set()
    for item in brief_input["evidence_pack"]:
        chunk_id = item.get("chunk_id")
        if isinstance(chunk_id, str) and chunk_id:
            evidence_ids.add(chunk_id)
    return evidence_ids


def _validate_issue_map(item: dict[str, Any], *, valid_evidence_ids: set[str]) -> IssueMap:
    list_fields = (
        "supporting_evidence_ids",
        "opposing_evidence_ids",
        "minority_evidence_ids",
        "watch_evidence_ids",
    )
    if not all(
        isinstance(item.get(field), str) and item[field].strip()
        for field in ("issue_id", "issue_question", "thesis_hint")
    ):
        raise ValueError("Malformed issue planner output.")
    for field in list_fields:
        values = item.get(field)
        if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
            raise ValueError("Malformed issue planner output.")
        if any(value not in valid_evidence_ids for value in values):
            raise ValueError("Malformed issue planner output.")
    return cast(IssueMap, item)
