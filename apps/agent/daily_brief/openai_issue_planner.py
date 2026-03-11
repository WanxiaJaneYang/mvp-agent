from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

from apps.agent.daily_brief.model_interfaces import IssuePlannerInput, IssuePlannerProvider
from apps.agent.pipeline.types import IssueMap


class OpenAIIssuePlanner(IssuePlannerProvider):
    def __init__(self, *, response_loader: Callable[[IssuePlannerInput], str | list[dict[str, Any]]] | None) -> None:
        self._response_loader = response_loader

    def plan_issues(self, *, brief_input: IssuePlannerInput) -> list[IssueMap]:
        if self._response_loader is None:
            raise ValueError("OpenAIIssuePlanner requires a response_loader for this local runtime slice.")
        payload = self._response_loader(brief_input)
        if isinstance(payload, str):
            parsed = json.loads(payload)
        else:
            parsed = payload
        if not isinstance(parsed, list):
            raise ValueError("Issue planner output must be a list.")

        issues: list[IssueMap] = []
        required_fields = set(IssueMap.__annotations__)
        for item in parsed:
            if not isinstance(item, dict) or set(item) != required_fields:
                raise ValueError("Malformed issue planner output.")
            issues.append(_validate_issue_map(item))
        return issues


def _validate_issue_map(item: dict[str, Any]) -> IssueMap:
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
    return cast(IssueMap, item)
