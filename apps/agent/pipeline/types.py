from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


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

    def to_dict(self) -> dict[str, object]:
        return {
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


@dataclass
class StageResult:
    status: RunStatus = RunStatus.OK
    error_summary: str | None = None
