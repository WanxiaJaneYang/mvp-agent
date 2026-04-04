from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, NotRequired, Required, TypedDict


class RunType(str, Enum):
    INGESTION = "ingestion"
    DAILY_BRIEF = "daily_brief"
    ALERT_SCAN = "alert_scan"
    ALERT_DISPATCH = "alert_dispatch"
    MAINTENANCE = "maintenance"


class RunStatus(str, Enum):
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"
    STOPPED_BUDGET = "stopped_budget"
    PARTIAL = "partial"


DailyBriefOutputSection = Literal["prevailing", "counter", "minority", "watch", "changed"]
DailyBriefClaimKind = Literal["prevailing", "counter", "minority", "watch"]
DailyBriefNoveltyLabel = Literal["new", "continued", "reframed", "weakened", "strengthened", "reversed", "unknown"]
DailyBriefRenderMode = Literal["full", "compressed"]
SourceScarcityMode = Literal["normal", "scarce"]
CitationValidationStatus = Literal["ok", "partial", "retry"]
FinalSynthesisStatus = Literal["ok", "partial", "abstained"]
CriticStatus = Literal["pass", "warn", "fail"]
IssueOverlapDecision = Literal["keep", "merge", "drop"]
IssueInformationGainDecision = Literal["keep", "drop"]
PublishDecisionStatus = Literal["publish", "hold"]
DeliveryMode = Literal["email_and_html", "html_only", "none"]


DAILY_BRIEF_OUTPUT_SECTIONS: tuple[DailyBriefOutputSection, ...] = (
    "prevailing",
    "counter",
    "minority",
    "watch",
    "changed",
)
DAILY_BRIEF_CORE_OUTPUT_SECTIONS: tuple[DailyBriefOutputSection, ...] = (
    "prevailing",
    "counter",
    "minority",
    "watch",
)
DAILY_BRIEF_OPTIONAL_OUTPUT_SECTIONS: tuple[DailyBriefOutputSection, ...] = ("changed",)
DAILY_BRIEF_CLAIM_SECTIONS: frozenset[DailyBriefOutputSection] = frozenset(
    DAILY_BRIEF_OUTPUT_SECTIONS
)
DAILY_BRIEF_SECTION_ALIASES: dict[str, DailyBriefOutputSection] = {
    "counterarguments": "counter",
    "what_to_watch": "watch",
    "what to watch": "watch",
}


class SourceRegistryEntry(TypedDict):
    id: Required[str]
    name: Required[str]
    url: Required[str]
    base_url: NotRequired[str]
    type: Required[str]
    fetch_via: NotRequired[str]
    source_role: NotRequired[str]
    timestamp_authority: NotRequired[str]
    content_mode: NotRequired[str]
    credibility_tier: Required[int]
    paywall_policy: Required[str]
    fetch_interval: Required[str]
    tags: NotRequired[list[str]]
    per_fetch_cap: NotRequired[int]


class PlannedFetchItem(TypedDict):
    source_id: str
    payload: dict[str, Any]


class SourceRow(TypedDict):
    source_id: str
    name: str
    base_url: str
    source_type: str
    credibility_tier: int
    paywall_policy: str
    fetch_interval: str
    tags_json: str
    enabled: int
    created_at: str
    updated_at: str


class SourceOperatorStateRow(TypedDict):
    source_id: str
    is_active: int
    strategy_state: str
    current_strategy_id: str | None
    latest_strategy_id: str | None
    last_onboarding_run_id: str | None
    last_collection_status: str
    last_collection_started_at: str | None
    last_collection_finished_at: str | None
    last_collection_error: str | None
    activated_at: str | None
    deactivated_at: str | None
    updated_at: str


class SourceStrategyVersionRow(TypedDict):
    strategy_id: str
    source_id: str
    version: int
    strategy_status: str
    entrypoint_url: str
    fetch_via: str
    content_mode: str
    parser_profile: str | None
    max_items_per_run: int
    strategy_summary_json: str
    strategy_details_json: str
    created_from_run_id: str | None
    created_at: str
    approved_at: str | None


class SourceOnboardingRunRow(TypedDict):
    onboarding_run_id: str
    source_id: str
    status: str
    worker_kind: str
    worker_ref: str | None
    submitted_at: str
    started_at: str | None
    finished_at: str | None
    proposed_strategy_id: str | None
    error_message: str | None
    result_summary_json: str | None


class ResolvedSource(TypedDict):
    source_id: str
    contract: SourceRegistryEntry
    operator_state: SourceOperatorStateRow
    current_strategy: SourceStrategyVersionRow | None
    latest_strategy: SourceStrategyVersionRow | None
    latest_onboarding_run: SourceOnboardingRunRow | None
    runtime_eligible: bool


class RuntimeDocumentRecord(TypedDict):
    source_id: str
    publisher: str
    canonical_url: str
    title: str | None
    author: str | None
    language: str | None
    doc_type: str | None
    published_at: str | None
    fetched_at: str
    paywall_policy: str
    metadata_only: int
    rss_snippet: str | None
    body_text: str | None
    content_hash: str
    status: str
    created_at: str
    updated_at: str
    doc_id: str
    credibility_tier: int
    ingestion_run_id: str


class RuntimeChunkRow(TypedDict):
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    token_count: int
    char_start: int
    char_end: int
    created_at: str


class FtsRow(TypedDict):
    text: str
    doc_id: str
    chunk_id: str
    publisher: str
    source_id: str
    published_at: str | None
    credibility_tier: NotRequired[int]


class EvidencePackItem(TypedDict):
    chunk_id: str
    source_id: str
    publisher: str
    credibility_tier: int
    retrieval_score: float
    semantic_score: float | None
    recency_score: float
    credibility_score: float
    rank_in_pack: int
    doc_id: str


class BriefPlan(TypedDict):
    brief_id: str
    brief_thesis: str
    top_takeaways: list[str]
    issue_budget: int
    render_mode: DailyBriefRenderMode
    source_scarcity_mode: SourceScarcityMode
    candidate_issue_seeds: list[str]
    issue_order: list[str]
    watchlist: list[str]
    reason_codes: list[str]


class IssueEvidenceCoverageSummary(TypedDict):
    unique_publishers: int
    source_roles: list[str]
    time_span_hours: float


class IssueEvidenceScope(TypedDict):
    issue_id: str
    issue_seed: str
    primary_chunk_ids: list[str]
    opposing_chunk_ids: list[str]
    minority_chunk_ids: list[str]
    watch_chunk_ids: list[str]
    coverage_summary: IssueEvidenceCoverageSummary


class IssueOverlapReport(TypedDict):
    left_issue_id: str
    right_issue_id: str
    question_token_overlap: float
    citation_overlap: float
    source_overlap: float
    thesis_overlap: str
    decision: IssueOverlapDecision
    reason_codes: list[str]


class IssueInformationGain(TypedDict):
    issue_id: str
    information_gain_score: float
    decision: IssueInformationGainDecision
    reason_codes: list[str]


class CitationStoreEntry(TypedDict):
    citation_id: str
    source_id: str
    publisher: str
    doc_id: str
    chunk_id: str
    url: str
    title: str | None
    published_at: str | None
    fetched_at: str | None
    paywall_policy: str
    quote_text: str | None
    snippet_text: str


class DailyBriefBullet(TypedDict, total=False):
    claim_id: str
    claim_kind: DailyBriefClaimKind
    text: str
    citation_ids: list[str]
    confidence_label: str
    validator_action: str
    claim_span_citations: list[list[str]]
    evidence: list["ClaimEvidenceItem"]
    why_it_matters: str
    novelty_vs_prior_brief: DailyBriefNoveltyLabel
    delta_label: DailyBriefNoveltyLabel
    delta_explanation: str

class DailyBriefMeta(TypedDict, total=False):
    status: str
    reason: str
    citation_status: str
    analytical_status: str
    publish_decision: PublishDecisionStatus
    reason_codes: list[str]


class ClaimEvidenceItem(TypedDict, total=False):
    citation_id: str
    publisher: str
    published_at: str | None
    support_text: str


class IssueMap(TypedDict):
    issue_id: str
    issue_question: str
    thesis_hint: str
    supporting_evidence_ids: list[str]
    opposing_evidence_ids: list[str]
    minority_evidence_ids: list[str]
    watch_evidence_ids: list[str]


class StructuredClaim(TypedDict):
    claim_id: str
    issue_id: str
    claim_kind: DailyBriefClaimKind
    claim_text: str
    supporting_citation_ids: list[str]
    opposing_citation_ids: list[str]
    confidence: str
    novelty_vs_prior_brief: DailyBriefNoveltyLabel
    why_it_matters: str


class ClaimDelta(TypedDict):
    claim_id: str
    prior_claim_ref: str | None
    novelty_label: DailyBriefNoveltyLabel
    delta_explanation: str
    supporting_prior_overlap: dict[str, Any]


class DailyBriefOverview(TypedDict, total=False):
    bottom_line: str
    top_takeaways: list[str]
    watchlist: list[str]
    render_mode: DailyBriefRenderMode
    source_scarcity_mode: SourceScarcityMode
    issue_budget: int


class DailyBriefIssue(TypedDict, total=False):
    issue_id: str
    issue_question: str
    title: str
    summary: str
    prevailing: list[DailyBriefBullet]
    counter: list[DailyBriefBullet]
    minority: list[DailyBriefBullet]
    watch: list[DailyBriefBullet]


class PublishDecision(TypedDict):
    citation_status: str
    analytical_status: str
    publish_decision: PublishDecisionStatus
    reason_codes: list[str]
    delivery_mode: DeliveryMode


class DailyBriefSynthesisV2(TypedDict, total=False):
    brief: DailyBriefOverview
    issues: list[DailyBriefIssue]
    meta: DailyBriefMeta
    changed: list[DailyBriefBullet]


class DailyBriefSynthesis(TypedDict, total=False):
    prevailing: list[DailyBriefBullet]
    counter: list[DailyBriefBullet]
    minority: list[DailyBriefBullet]
    watch: list[DailyBriefBullet]
    changed: list[DailyBriefBullet]
    meta: DailyBriefMeta


ValidatedDailyBriefSynthesis = DailyBriefSynthesis | DailyBriefSynthesisV2


class CitationValidationReport(TypedDict):
    total_bullets: int
    cited_bullets: int
    removed_bullets: int
    validation_passed: bool
    should_retry: bool
    empty_core_sections: list[str]
    synthesis: ValidatedDailyBriefSynthesis
    citation_store: dict[str, CitationStoreEntry]


class CitationValidationResult(TypedDict):
    status: CitationValidationStatus
    synthesis: ValidatedDailyBriefSynthesis
    citation_store: dict[str, CitationStoreEntry]
    report: CitationValidationReport
    validation_attempts: int
    max_validation_attempts: int
    retry_exhausted: bool


class FinalSynthesisResult(TypedDict):
    status: FinalSynthesisStatus
    synthesis: ValidatedDailyBriefSynthesis
    report: CitationValidationReport | None
    abstain_reason: str | None


class CriticReport(TypedDict):
    status: CriticStatus
    reason_codes: list[str]
    flagged_claim_ids: list[str]


class DailyBriefSectionBulletRow(TypedDict):
    synthesis_id: str
    section: DailyBriefOutputSection
    bullet_index: int
    text: str
    claim_span_count: int
    is_abstain: int
    confidence_label: str | None


class BulletCitationRow(TypedDict):
    synthesis_id: str
    section: DailyBriefOutputSection
    bullet_index: int
    claim_span_index: int
    citation_id: str


@dataclass
class RunCounters:
    docs_fetched: int = 0
    docs_ingested: int = 0
    chunks_indexed: int = 0
    tool_calls: int = 0
    pages_fetched: int = 0
    model_input_tokens: int = 0
    model_output_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class RunContext:
    run_id: str
    run_type: RunType
    started_at: str
    status: RunStatus
    ended_at: str | None = None
    error_summary: str | None = None
    counters: RunCounters = field(default_factory=RunCounters)
    budget_snapshot: dict[str, object] | None = None
    budget_ledger_rows: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "run_id": self.run_id,
            "run_type": self.run_type.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status.value,
            "docs_fetched": self.counters.docs_fetched,
            "docs_ingested": self.counters.docs_ingested,
            "chunks_indexed": self.counters.chunks_indexed,
            "tool_calls": self.counters.tool_calls,
            "pages_fetched": self.counters.pages_fetched,
            "model_input_tokens": self.counters.model_input_tokens,
            "model_output_tokens": self.counters.model_output_tokens,
            "estimated_cost_usd": self.counters.estimated_cost_usd,
            "error_summary": self.error_summary,
            "created_at": self.started_at,
        }
        if self.budget_snapshot is not None:
            payload["budget_snapshot"] = dict(self.budget_snapshot)
        if self.budget_ledger_rows:
            payload["budget_ledger_rows"] = [dict(row) for row in self.budget_ledger_rows]
        return payload


@dataclass
class StageResult:
    status: RunStatus = RunStatus.OK
    error_summary: str | None = None
    retryable: bool = False


@dataclass
class DailyBriefInputStageData:
    registry: dict[str, SourceRegistryEntry]
    active_sources: list[SourceRegistryEntry]
    planned_items: list[PlannedFetchItem]
    source_rows: list[SourceRow]


@dataclass
class DailyBriefCorpusStageData:
    source_rows: list[SourceRow]
    documents: list[RuntimeDocumentRecord]
    chunks: list[RuntimeChunkRow]
    fts_rows: list[FtsRow]
    corpus_items: list[EvidencePackItem] = field(default_factory=list)
    diversity_stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class DailyBriefSynthesisStageData:
    query_text: str
    corpus_summary: list[str]
    brief_plan: BriefPlan
    evidence_pack_items: list[EvidencePackItem]
    evidence_pack_report: dict[str, Any]
    issue_evidence_scopes: list[IssueEvidenceScope]
    issue_map: list[IssueMap]
    issue_overlap_reports: list[IssueOverlapReport]
    information_gain_reports: list[IssueInformationGain]
    structured_claims: list[StructuredClaim]
    claim_deltas: list[ClaimDelta]
    publish_decision: PublishDecision
    citation_store: dict[str, CitationStoreEntry]
    stage8_result: CitationValidationResult
    final_result: FinalSynthesisResult
    critic_report: CriticReport | None
    citation_rows: list[CitationStoreEntry]
    synthesis_bullet_rows: list[DailyBriefSectionBulletRow]
    bullet_citation_rows: list[BulletCitationRow]
