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
CitationValidationStatus = Literal["ok", "partial", "retry"]
FinalSynthesisStatus = Literal["ok", "partial", "abstained"]


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
DAILY_BRIEF_CLAIM_SECTIONS: frozenset[DailyBriefOutputSection] = frozenset(DAILY_BRIEF_OUTPUT_SECTIONS)
DAILY_BRIEF_SECTION_ALIASES: dict[str, DailyBriefOutputSection] = {
    "counterarguments": "counter",
    "what_to_watch": "watch",
    "what to watch": "watch",
}


class SourceRegistryEntry(TypedDict):
    id: Required[str]
    name: Required[str]
    url: Required[str]
    type: Required[str]
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
    credibility_tier: int


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
    text: str
    citation_ids: list[str]
    confidence_label: str
    validator_action: str
    claim_span_citations: list[list[str]]


class DailyBriefMeta(TypedDict):
    status: str
    reason: str


class DailyBriefSynthesis(TypedDict, total=False):
    prevailing: list[DailyBriefBullet]
    counter: list[DailyBriefBullet]
    minority: list[DailyBriefBullet]
    watch: list[DailyBriefBullet]
    changed: list[DailyBriefBullet]
    meta: DailyBriefMeta


class CitationValidationReport(TypedDict):
    total_bullets: int
    cited_bullets: int
    removed_bullets: int
    validation_passed: bool
    should_retry: bool
    empty_core_sections: list[str]
    synthesis: DailyBriefSynthesis
    citation_store: dict[str, CitationStoreEntry]


class CitationValidationResult(TypedDict):
    status: CitationValidationStatus
    synthesis: DailyBriefSynthesis
    citation_store: dict[str, CitationStoreEntry]
    report: CitationValidationReport
    validation_attempts: int
    max_validation_attempts: int
    retry_exhausted: bool


class FinalSynthesisResult(TypedDict):
    status: FinalSynthesisStatus
    synthesis: DailyBriefSynthesis
    report: CitationValidationReport | None
    abstain_reason: str | None


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


@dataclass
class DailyBriefSynthesisStageData:
    query_text: str
    evidence_pack_items: list[EvidencePackItem]
    evidence_pack_report: dict[str, Any]
    citation_store: dict[str, CitationStoreEntry]
    stage8_result: CitationValidationResult
    final_result: FinalSynthesisResult
    citation_rows: list[CitationStoreEntry]
    synthesis_bullet_rows: list[DailyBriefSectionBulletRow]
    bullet_citation_rows: list[BulletCitationRow]
