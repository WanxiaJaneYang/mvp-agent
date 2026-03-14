from __future__ import annotations

from typing import Any, Mapping

VALIDATOR_PLACEHOLDER_TEXT = "[Insufficient evidence to support this claim]"
VALIDATOR_PLACEHOLDER_ACTION = "replaced_insufficient_evidence"
ABSTAIN_PLACEHOLDER_TEXT = "[Insufficient evidence to produce a validated output]"


def is_validator_placeholder_bullet(bullet: Mapping[str, Any]) -> bool:
    return (
        str(bullet.get("text", "")) == VALIDATOR_PLACEHOLDER_TEXT
        or str(bullet.get("validator_action", "")) == VALIDATOR_PLACEHOLDER_ACTION
    )


def is_abstain_placeholder_bullet(bullet: Mapping[str, Any]) -> bool:
    return str(bullet.get("text", "")) == ABSTAIN_PLACEHOLDER_TEXT


def is_abstain_fallback_bullet(bullet: Mapping[str, Any]) -> bool:
    return is_abstain_placeholder_bullet(bullet) or is_validator_placeholder_bullet(bullet)
