from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _make_snapshot(*, run_id: str, run_type: str, started_at: str, status: str, ended_at: str | None = None) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "run_type": run_type,
        "started_at": started_at,
        "ended_at": ended_at,
        "status": status,
    }


def run_pipeline(
    *,
    run_id: str,
    run_type: str,
    stages: Iterable[Callable[[dict[str, Any]], dict[str, Any]]],
    recorder: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    started_at = _utc_now_iso()
    context = {"run_id": run_id, "run_type": run_type, "started_at": started_at, "status": "running"}
    recorder(_make_snapshot(run_id=run_id, run_type=run_type, started_at=started_at, status="running"))

    final_status = "ok"
    for stage in stages:
        stage_result = stage(context)
        final_status = stage_result.get("status", "ok")
        context.update(stage_result)

    context["status"] = final_status
    recorder(
        _make_snapshot(
            run_id=run_id,
            run_type=run_type,
            started_at=started_at,
            ended_at=_utc_now_iso(),
            status=final_status,
        )
    )
    return context
