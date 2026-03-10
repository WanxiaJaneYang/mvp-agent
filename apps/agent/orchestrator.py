from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping

from apps.agent.pipeline.stages import PipelineStage, should_retry
from apps.agent.pipeline.types import RunContext, RunStatus, RunType, StageResult
from apps.agent.runtime.budget_guard import evaluate_budget_guard
from apps.agent.runtime.cost_ledger import build_budget_ledger_rows


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
    budget_preflight: Mapping[str, Any] | None = None,
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

    if budget_preflight is not None:
        decision = evaluate_budget_guard(
            hourly_spend_usd=budget_preflight["hourly_spend_usd"],
            daily_spend_usd=budget_preflight["daily_spend_usd"],
            monthly_spend_usd=budget_preflight["monthly_spend_usd"],
            next_estimated_cost_usd=budget_preflight["next_estimated_cost_usd"],
            caps=budget_preflight["caps"],
        )
        budget_ledger_rows = build_budget_ledger_rows(
            run_id=run_id,
            recorded_at=started_at,
            decision=decision,
            windows=budget_preflight["windows"],
        )
        context.budget_snapshot = {
            "hourly_spend_usd": decision.projected_spend["hourly"],
            "hourly_cap_usd": decision.caps["hourly"],
            "daily_spend_usd": decision.projected_spend["daily"],
            "daily_cap_usd": decision.caps["daily"],
            "monthly_spend_usd": decision.projected_spend["monthly"],
            "monthly_cap_usd": decision.caps["monthly"],
            "allowed": decision.allowed,
        }
        context.budget_ledger_rows = budget_ledger_rows
        if not decision.allowed:
            context.status = RunStatus.STOPPED_BUDGET
            context.ended_at = _utc_now_iso()
            context.error_summary = decision.reason
            stopped_result = context.to_dict()
            recorder(stopped_result)
            return stopped_result

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
            if stage_result.error_summary is not None:
                context.error_summary = stage_result.error_summary
            if should_retry(stage_result) and attempts < max_stage_attempts:
                continue
            break

        if stage_result.status == RunStatus.PARTIAL:
            final_status = RunStatus.PARTIAL
            continue

        if stage_result.status == RunStatus.OK:
            continue

        final_status = stage_result.status
        break

    context.status = final_status
    context.ended_at = _utc_now_iso()
    recorder(context.to_dict())
    return context.to_dict()
