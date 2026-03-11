from __future__ import annotations

from typing import Any, Protocol, TypedDict

from apps.agent.pipeline.types import CriticReport, IssueMap, StructuredClaim


class IssuePlannerInput(TypedDict):
    run_id: str
    generated_at_utc: str
    evidence_pack: list[dict[str, Any]]
    prior_brief_context: dict[str, Any] | None


class ClaimComposerInput(TypedDict):
    run_id: str
    generated_at_utc: str
    issue_map: list[IssueMap]
    citation_store: dict[str, dict[str, Any]]
    prior_brief_context: dict[str, Any] | None


class CriticInput(TypedDict):
    run_id: str
    generated_at_utc: str
    synthesis: dict[str, Any]
    citation_store: dict[str, dict[str, Any]]
    prior_brief_context: dict[str, Any] | None


class IssuePlannerProvider(Protocol):
    def plan_issues(self, *, brief_input: IssuePlannerInput) -> list[IssueMap]:
        ...


class ClaimComposerProvider(Protocol):
    def compose_claims(self, *, brief_input: ClaimComposerInput) -> list[StructuredClaim]:
        ...


class CriticProvider(Protocol):
    def review_brief(self, *, brief_input: CriticInput) -> CriticReport:
        ...
