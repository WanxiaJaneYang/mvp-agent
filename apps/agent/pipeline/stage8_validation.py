from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from apps.agent.validators.citation_validator import validate_synthesis


def run_stage8_citation_validation(
    synthesis: Mapping[str, Iterable[Any]],
    citation_store: Mapping[str, Mapping[str, Any]],
    *,
    replace_with_placeholder: bool = True,
    max_removed_without_retry: int = 3,
) -> Dict[str, Any]:
    report = validate_synthesis(
        synthesis,
        citation_store,
        replace_with_placeholder=replace_with_placeholder,
        max_removed_without_retry=max_removed_without_retry,
    )

    if report.should_retry:
        status = "retry"
    elif report.removed_bullets > 0:
        status = "partial"
    else:
        status = "ok"

    return {
        "status": status,
        "synthesis": report.synthesis,
        "citation_store": report.citation_store,
        "report": report.to_dict(),
    }
