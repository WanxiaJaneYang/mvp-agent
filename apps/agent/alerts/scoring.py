from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AlertCategory = Literal["policy", "macro_release", "corporate_event", "narrative_shift"]
AlertDecisionBand = Literal["send", "bundle", "suppress"]


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


@dataclass(frozen=True)
class AlertScoreInputs:
    importance: float
    evidence_strength: float
    confidence: float
    portfolio_relevance: float
    noise_risk: float

    def normalized(self) -> AlertScoreInputs:
        return AlertScoreInputs(
            importance=_clamp_score(self.importance),
            evidence_strength=_clamp_score(self.evidence_strength),
            confidence=_clamp_score(self.confidence),
            portfolio_relevance=_clamp_score(self.portfolio_relevance),
            noise_risk=_clamp_score(self.noise_risk),
        )


@dataclass(frozen=True)
class AlertScoreResult:
    category: AlertCategory
    total_score: float
    decision_band: AlertDecisionBand
    category_floor_met: bool
    inputs: AlertScoreInputs


def compute_alert_score(*, category: AlertCategory, inputs: AlertScoreInputs) -> AlertScoreResult:
    normalized = inputs.normalized()
    total = round(
        normalized.importance * 0.30
        + normalized.evidence_strength * 0.25
        + normalized.confidence * 0.20
        + normalized.portfolio_relevance * 0.15
        - normalized.noise_risk * 0.10,
        2,
    )
    total = _clamp_score(total)
    category_floor_met = _category_floor_met(category=category, inputs=normalized)
    decision_band = _decision_band(total_score=total, category_floor_met=category_floor_met)
    return AlertScoreResult(
        category=category,
        total_score=total,
        decision_band=decision_band,
        category_floor_met=category_floor_met,
        inputs=normalized,
    )


def _decision_band(*, total_score: float, category_floor_met: bool) -> AlertDecisionBand:
    if not category_floor_met:
        return "suppress"
    if total_score >= 70.0:
        return "send"
    if total_score >= 55.0:
        return "bundle"
    return "suppress"


def _category_floor_met(*, category: AlertCategory, inputs: AlertScoreInputs) -> bool:
    if category in {"policy", "macro_release"}:
        return inputs.importance >= 60.0
    if category == "corporate_event":
        return inputs.importance >= 55.0 and inputs.portfolio_relevance >= 35.0
    if category == "narrative_shift":
        return inputs.evidence_strength >= 60.0 and inputs.confidence >= 55.0
    return False
