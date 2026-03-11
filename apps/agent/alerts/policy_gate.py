from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from apps.agent.alerts.scoring import AlertCategory, AlertScoreInputs, AlertScoreResult, compute_alert_score

AlertPolicyAction = Literal["send", "bundle", "suppress"]
SuppressionReason = Literal[
    "below_threshold",
    "failed_quality_gate",
    "cooldown_active",
    "daily_cap_reached",
    "budget_stopped",
]


@dataclass(frozen=True)
class AlertEvidenceSummary:
    source_ids: tuple[str, ...]
    credibility_tiers: tuple[int, ...]
    citation_count: int
    max_publisher_pct: float
    tier_1_2_pct: float
    tier_4_pct: float
    paywall_safe: bool


@dataclass(frozen=True)
class AlertCandidate:
    category: AlertCategory
    triggered_at: str
    score_inputs: AlertScoreInputs
    evidence: AlertEvidenceSummary


@dataclass(frozen=True)
class AlertPolicyContext:
    daily_alerts_sent: int
    last_alert_sent_at: str | None
    budget_allowed: bool
    max_alerts_per_day: int = 3
    cooldown_minutes: int = 60


@dataclass(frozen=True)
class AlertPolicyDecision:
    action: AlertPolicyAction
    score: AlertScoreResult
    suppression_reason: SuppressionReason | None
    bundle_for_daily_brief: bool


def evaluate_alert_policy(
    *,
    candidate: AlertCandidate,
    context: AlertPolicyContext,
) -> AlertPolicyDecision:
    score = compute_alert_score(category=candidate.category, inputs=candidate.score_inputs)

    if not context.budget_allowed:
        return AlertPolicyDecision(
            action="suppress",
            score=score,
            suppression_reason="budget_stopped",
            bundle_for_daily_brief=False,
        )

    if not _quality_gate_passed(candidate.evidence):
        return AlertPolicyDecision(
            action="suppress",
            score=score,
            suppression_reason="failed_quality_gate",
            bundle_for_daily_brief=False,
        )

    if score.decision_band == "suppress":
        return AlertPolicyDecision(
            action="suppress",
            score=score,
            suppression_reason="below_threshold",
            bundle_for_daily_brief=False,
        )

    if score.decision_band == "bundle":
        return AlertPolicyDecision(
            action="bundle",
            score=score,
            suppression_reason=None,
            bundle_for_daily_brief=True,
        )

    if context.daily_alerts_sent >= context.max_alerts_per_day:
        return AlertPolicyDecision(
            action="suppress",
            score=score,
            suppression_reason="daily_cap_reached",
            bundle_for_daily_brief=True,
        )

    if _cooldown_active(
        triggered_at=candidate.triggered_at,
        last_alert_sent_at=context.last_alert_sent_at,
        cooldown_minutes=context.cooldown_minutes,
    ):
        return AlertPolicyDecision(
            action="suppress",
            score=score,
            suppression_reason="cooldown_active",
            bundle_for_daily_brief=True,
        )

    return AlertPolicyDecision(
        action="send",
        score=score,
        suppression_reason=None,
        bundle_for_daily_brief=False,
    )


def _quality_gate_passed(evidence: AlertEvidenceSummary) -> bool:
    if evidence.citation_count < 1:
        return False
    if evidence.max_publisher_pct > 40.0:
        return False
    if evidence.tier_1_2_pct < 50.0:
        return False
    if evidence.tier_4_pct > 15.0:
        return False
    if not evidence.paywall_safe:
        return False

    if any(tier == 1 for tier in evidence.credibility_tiers):
        return True

    tier_two_sources = {
        source_id
        for source_id, tier in zip(evidence.source_ids, evidence.credibility_tiers, strict=False)
        if tier == 2
    }
    return len(tier_two_sources) >= 2


def _cooldown_active(*, triggered_at: str, last_alert_sent_at: str | None, cooldown_minutes: int) -> bool:
    if last_alert_sent_at is None:
        return False
    current = _parse_utc_iso(triggered_at)
    previous = _parse_utc_iso(last_alert_sent_at)
    return current - previous < timedelta(minutes=cooldown_minutes)


def _parse_utc_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
