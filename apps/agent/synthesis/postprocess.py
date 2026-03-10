from __future__ import annotations

from apps.agent.pipeline.types import DailyBriefBullet, DailyBriefSynthesis, FinalSynthesisResult


ABSTAIN_TEXT = "[Insufficient evidence to produce a validated output]"
CORE_SECTIONS = ("prevailing", "counter", "minority", "watch")


def build_abstain_synthesis(*, reason: str) -> DailyBriefSynthesis:
    bullet: DailyBriefBullet = {
        "text": ABSTAIN_TEXT,
        "citation_ids": [],
        "confidence_label": "abstained",
    }
    synthesis = {section: [dict(bullet)] for section in CORE_SECTIONS}
    synthesis["meta"] = {
        "status": "abstained",
        "reason": reason,
    }
    return synthesis


def finalize_validation_outcome(*, validation_result: dict[str, object]) -> FinalSynthesisResult:
    status = validation_result["status"]
    if status in {"ok", "partial"}:
        return {
            "status": status,
            "synthesis": validation_result["synthesis"],
            "report": validation_result.get("report"),
            "abstain_reason": None,
        }

    if not bool(validation_result.get("retry_exhausted", False)):
        raise ValueError("Validation retry policy must be exhausted before abstaining.")

    abstain_reason = "validation_retry_exhausted"
    return {
        "status": "abstained",
        "synthesis": build_abstain_synthesis(reason=abstain_reason),
        "report": validation_result.get("report"),
        "abstain_reason": abstain_reason,
    }
