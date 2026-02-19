from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional


@dataclass
class BudgetCaps:
    hourly_usd: float = 0.10
    daily_usd: float = 3.0
    monthly_usd: float = 100.0


@dataclass
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
    def to_decimal(value: float) -> Decimal:
        return Decimal(str(value))

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

    incremental_cost = max(next_estimated_cost_usd, 0.0)
    incremental_cost_d = to_decimal(incremental_cost)
    projected_raw = {
        "hourly": to_decimal(hourly_spend_usd) + incremental_cost_d,
        "daily": to_decimal(daily_spend_usd) + incremental_cost_d,
        "monthly": to_decimal(monthly_spend_usd) + incremental_cost_d,
    }
    cent = Decimal("0.01")
    projected = {
        "hourly": float(projected_raw["hourly"].quantize(cent, rounding=ROUND_HALF_UP)),
        "daily": float(projected_raw["daily"].quantize(cent, rounding=ROUND_HALF_UP)),
        "monthly": float(projected_raw["monthly"].quantize(cent, rounding=ROUND_HALF_UP)),
    }
    cap_map = {
        "hourly": to_decimal(caps.hourly_usd),
        "daily": to_decimal(caps.daily_usd),
        "monthly": to_decimal(caps.monthly_usd),
    }

    exceeded: List[str] = []
    for window in ("hourly", "daily", "monthly"):
        if projected_raw[window] >= cap_map[window]:
            exceeded.append(window)

    if exceeded:
        reason = (
            "Budget hard-stop triggered: projected spend reaches or exceeds "
            + ", ".join(exceeded)
            + " cap(s)."
        )
        return BudgetDecision(
            allowed=False,
            exceeded_windows=exceeded,
            reason=reason,
            projected_spend=projected,
            caps={k: float(v) for k, v in cap_map.items()},
        )

    return BudgetDecision(
        allowed=True,
        exceeded_windows=[],
        reason=None,
        projected_spend=projected,
        caps={k: float(v) for k, v in cap_map.items()},
    )

