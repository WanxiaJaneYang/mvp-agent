from __future__ import annotations

from typing import Any


ABSTAIN_TEXT = "[Insufficient evidence to produce a validated output]"
CORE_SECTIONS = ("prevailing", "counter", "minority", "watch")


def build_abstain_synthesis(*, reason: str) -> dict[str, Any]:
    bullet = {
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
