from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from apps.agent.pipeline.stages import PipelineStage, should_retry
from apps.agent.pipeline.types import RunContext, RunStatus, RunType, StageResult

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_run_type(run_type: str | RunType) -> RunType:
    if isinstance(run_type, RunType):
        return run_type
    try:
        return RunType(run_type)
    except ValueError as exc:
        raise ValueError(f"Unsupported run_type: {run_type}") from exc


def run_pipeline(
    *,
    run_id: str,
    run_type: str | RunType,
    stages: Iterable[PipelineStage],
    recorder: Callable[[dict[str, Any]], None],
    max_stage_attempts: int = 1,
) -> dict[str, Any]:
    started_at = _utc_now_iso()
    normalized_run_type = _normalize_run_type(run_type)
    context = RunContext(
        run_id=run_id,
        run_type=normalized_run_type,
        started_at=started_at,
        status=RunStatus.RUNNING,
    )
    recorder(context.to_dict())

    final_status = RunStatus.OK
    for stage in stages:
        attempts = 0
        while True:
            attempts += 1
            stage_result = stage(context)
            if isinstance(stage_result, dict):
                stage_result = StageResult(
                    status=RunStatus(stage_result.get("status", RunStatus.OK)),
                    error_summary=stage_result.get("error_summary"),
                    retryable=stage_result.get("retryable", False),
                )
            final_status = stage_result.status
            if stage_result.error_summary is not None:
                context.error_summary = stage_result.error_summary
            if should_retry(stage_result) and attempts < max_stage_attempts:
                continue
            break

    context.status = final_status
    context.ended_at = _utc_now_iso()
    recorder(context.to_dict())
    return context.to_dict()
