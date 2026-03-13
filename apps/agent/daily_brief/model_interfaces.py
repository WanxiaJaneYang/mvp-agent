from __future__ import annotations

from typing import Any, Protocol, TypedDict

from apps.agent.pipeline.types import BriefPlan, CriticReport, IssueEvidenceScope, IssueMap, StructuredClaim


class BriefPlannerInput(TypedDict):
    run_id: str
    generated_at_utc: str
    corpus_summary: list[str]
    source_diversity_stats: dict[str, Any]
    prior_brief_context: dict[str, Any] | None


class IssuePlannerInput(TypedDict):
    run_id: str
    generated_at_utc: str
    brief_plan: BriefPlan
    issue_evidence_scopes: list[IssueEvidenceScope]
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


class BriefPlannerProvider(Protocol):
    def plan_brief(self, *, brief_input: BriefPlannerInput) -> BriefPlan:
        ...


class ClaimComposerProvider(Protocol):
    def compose_claims(self, *, brief_input: ClaimComposerInput) -> list[StructuredClaim]:
        ...


class CriticProvider(Protocol):
    def review_brief(self, *, brief_input: CriticInput) -> CriticReport:
        ...
