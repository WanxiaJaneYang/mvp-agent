from __future__ import annotations

from typing import Protocol

from apps.agent.pipeline.types import RunContext, StageResult


class PipelineStage(Protocol):
    def __call__(self, context: RunContext) -> StageResult:
        ...
