from __future__ import annotations

from typing import Protocol

from apps.agent.pipeline.types import RunContext, RunStatus, StageResult


class PipelineStage(Protocol):
    def __call__(self, context: RunContext) -> StageResult: ...


def should_retry(result: StageResult) -> bool:
    return result.retryable and result.status == RunStatus.FAILED
