from __future__ import annotations

from apps.agent.pipeline.types import (
    CitationValidationResult,
    DailyBriefBullet,
    DailyBriefSynthesis,
    FinalSynthesisResult,
)

ABSTAIN_TEXT = "[Insufficient evidence to produce a validated output]"
CORE_SECTIONS = ("prevailing", "counter", "minority", "watch")


def _build_abstain_bullet() -> DailyBriefBullet:
    return {
        "text": ABSTAIN_TEXT,
        "citation_ids": [],
        "confidence_label": "abstained",
    }


def build_abstain_synthesis(*, reason: str) -> DailyBriefSynthesis:
    synthesis: DailyBriefSynthesis = {
        "prevailing": [_build_abstain_bullet()],
        "counter": [_build_abstain_bullet()],
        "minority": [_build_abstain_bullet()],
        "watch": [_build_abstain_bullet()],
    }
    synthesis["meta"] = {
        "status": "abstained",
        "reason": reason,
    }
    return synthesis


def finalize_validation_outcome(
    *, validation_result: CitationValidationResult
) -> FinalSynthesisResult:
    if validation_result["status"] == "ok":
        return {
            "status": "ok",
            "synthesis": validation_result["synthesis"],
            "report": validation_result["report"],
            "abstain_reason": None,
        }

    if validation_result["status"] == "partial":
        return {
            "status": "partial",
            "synthesis": validation_result["synthesis"],
            "report": validation_result["report"],
            "abstain_reason": None,
        }

    if not validation_result["retry_exhausted"]:
        raise ValueError("Validation retry policy must be exhausted before abstaining.")

    abstain_reason = "validation_retry_exhausted"
    return {
        "status": "abstained",
        "synthesis": build_abstain_synthesis(reason=abstain_reason),
        "report": validation_result["report"],
        "abstain_reason": abstain_reason,
    }
