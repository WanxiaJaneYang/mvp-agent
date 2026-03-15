from __future__ import annotations

from typing import cast

from apps.agent.daily_brief.placeholders import ABSTAIN_PLACEHOLDER_TEXT
from apps.agent.pipeline.types import (
    CitationValidationResult,
    DailyBriefBullet,
    DailyBriefMeta,
    DailyBriefSynthesisV2,
    FinalSynthesisResult,
)

CORE_SECTIONS = ("prevailing", "counter", "minority", "watch")


def _build_abstain_bullet() -> DailyBriefBullet:
    return {
        "text": ABSTAIN_PLACEHOLDER_TEXT,
        "citation_ids": [],
        "confidence_label": "abstained",
    }


def build_abstain_synthesis(*, reason: str) -> DailyBriefSynthesisV2:
    return {
        "issues": [
            {
                "issue_id": "issue_abstain",
                "issue_question": "Insufficient evidence for a validated issue review",
                "title": "Insufficient evidence for a validated issue review",
                "summary": "The available evidence did not support a full literature review.",
                "prevailing": [_build_abstain_bullet()],
                "counter": [_build_abstain_bullet()],
                "minority": [_build_abstain_bullet()],
                "watch": [_build_abstain_bullet()],
            }
        ],
        "meta": {
            "status": "abstained",
            "reason": reason,
        },
    }


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
    validated_synthesis = validation_result["synthesis"]
    if isinstance(validated_synthesis.get("issues"), list):
        abstained_synthesis = cast(DailyBriefSynthesisV2, dict(validated_synthesis))
        current_meta = validated_synthesis.get("meta")
        meta = dict(current_meta) if isinstance(current_meta, dict) else {}
        meta["status"] = "abstained"
        meta["reason"] = abstain_reason
        abstained_synthesis["meta"] = cast(DailyBriefMeta, meta)
        synthesis = abstained_synthesis
    else:
        synthesis = build_abstain_synthesis(reason=abstain_reason)
    return {
        "status": "abstained",
        "synthesis": synthesis,
        "report": validation_result["report"],
        "abstain_reason": abstain_reason,
    }
