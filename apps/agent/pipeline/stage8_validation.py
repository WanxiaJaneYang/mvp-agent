from __future__ import annotations

from typing import Any, Collection, Iterable, Mapping

from apps.agent.pipeline.types import CitationValidationResult
from apps.agent.validators.citation_validator import validate_synthesis


def run_stage8_citation_validation(
    synthesis: Mapping[str, Iterable[Any]],
    citation_store: Mapping[str, Mapping[str, Any]],
    *,
    source_registry: Mapping[str, Mapping[str, Any]] | None = None,
    available_source_ids: Collection[str] | None = None,
    replace_with_placeholder: bool = True,
    max_removed_without_retry: int = 3,
) -> CitationValidationResult:
    report = validate_synthesis(
        synthesis,
        citation_store,
        source_registry=source_registry,
        available_source_ids=available_source_ids,
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
        "validation_attempts": 1,
        "max_validation_attempts": 1,
        "retry_exhausted": status == "retry",
    }
