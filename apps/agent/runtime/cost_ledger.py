from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from apps.agent.runtime.budget_guard import BudgetDecision


@dataclass(frozen=True)
class BudgetWindowSnapshot:
    window_start: str
    window_end: str
    cost_usd: float


def build_budget_ledger_rows(
    *,
    run_id: str,
    recorded_at: str,
    decision: BudgetDecision,
    windows: Mapping[str, BudgetWindowSnapshot],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for window_type in ("hourly", "daily", "monthly"):
        window = windows[window_type]
        rows.append(
            {
                "ledger_id": f"ledger_{run_id}_{window_type}",
                "run_id": run_id,
                "recorded_at": recorded_at,
                "window_type": window_type,
                "window_start": window.window_start,
                "window_end": window.window_end,
                "cost_usd": window.cost_usd,
                "cap_usd": decision.caps[window_type],
                "exceeded": 1 if window_type in decision.exceeded_windows else 0,
            }
        )
    return rows
