from __future__ import annotations

from typing import Any, Collection, Iterable, Mapping, cast

from apps.agent.pipeline.types import (
    CitationStoreEntry,
    CitationValidationReport,
    CitationValidationResult,
    CitationValidationStatus,
    ValidatedDailyBriefSynthesis,
)
from apps.agent.validators.citation_validator import validate_synthesis


def run_stage8_citation_validation(
    synthesis: ValidatedDailyBriefSynthesis,
    citation_store: Mapping[str, CitationStoreEntry],
    *,
    source_registry: Mapping[str, Mapping[str, Any]] | None = None,
    available_source_ids: Collection[str] | None = None,
    replace_with_placeholder: bool = True,
    max_removed_without_retry: int = 3,
) -> CitationValidationResult:
    report = validate_synthesis(
        cast(Mapping[str, Iterable[Any]], synthesis),
        citation_store,
        source_registry=source_registry,
        available_source_ids=available_source_ids,
        replace_with_placeholder=replace_with_placeholder,
        max_removed_without_retry=max_removed_without_retry,
    )

    status: CitationValidationStatus
    if report.should_retry:
        status = "retry"
    elif report.removed_bullets > 0:
        status = "partial"
    else:
        status = "ok"

    return {
        "status": status,
        "synthesis": cast(ValidatedDailyBriefSynthesis, report.synthesis),
        "citation_store": cast(dict[str, CitationStoreEntry], report.citation_store),
        "report": cast(CitationValidationReport, report.to_dict()),
        "validation_attempts": 1,
        "max_validation_attempts": 1,
        "retry_exhausted": status == "retry",
    }
