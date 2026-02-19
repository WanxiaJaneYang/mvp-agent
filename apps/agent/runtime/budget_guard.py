from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class BudgetCaps:
    hourly_usd: float = 0.10
    daily_usd: float = 3.0
    monthly_usd: float = 100.0


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    exceeded_windows: List[str]
    reason: Optional[str]
    projected_spend: Dict[str, float]
    caps: Dict[str, float]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def evaluate_budget_guard(
    *,
    hourly_spend_usd: float,
    daily_spend_usd: float,
    monthly_spend_usd: float,
    next_estimated_cost_usd: float,
    caps: BudgetCaps = BudgetCaps(),
) -> BudgetDecision:
    if hourly_spend_usd < 0.0:
        raise ValueError("hourly_spend_usd must be non-negative")
    if daily_spend_usd < 0.0:
        raise ValueError("daily_spend_usd must be non-negative")
    if monthly_spend_usd < 0.0:
        raise ValueError("monthly_spend_usd must be non-negative")
    if caps.hourly_usd <= 0.0:
        raise ValueError("caps.hourly_usd must be positive")
    if caps.daily_usd <= 0.0:
        raise ValueError("caps.daily_usd must be positive")
    if caps.monthly_usd <= 0.0:
        raise ValueError("caps.monthly_usd must be positive")

    projected = {
        "hourly": round(hourly_spend_usd + max(next_estimated_cost_usd, 0.0), 2),
        "daily": round(daily_spend_usd + max(next_estimated_cost_usd, 0.0), 2),
        "monthly": round(monthly_spend_usd + max(next_estimated_cost_usd, 0.0), 2),
    }
    cap_map = {
        "hourly": caps.hourly_usd,
        "daily": caps.daily_usd,
        "monthly": caps.monthly_usd,
    }

    exceeded: List[str] = []
    for window in ("hourly", "daily", "monthly"):
        if projected[window] >= cap_map[window]:
            exceeded.append(window)

    if exceeded:
        reason = (
            "Budget hard-stop triggered: projected spend exceeds "
            + ", ".join(exceeded)
            + " cap(s)."
        )
        return BudgetDecision(
            allowed=False,
            exceeded_windows=exceeded,
            reason=reason,
            projected_spend=projected,
            caps=cap_map,
        )

    return BudgetDecision(
        allowed=True,
        exceeded_windows=[],
        reason=None,
        projected_spend=projected,
        caps=cap_map,
    )

