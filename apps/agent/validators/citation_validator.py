from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping
from urllib.parse import urlparse

CORE_SECTIONS = ("prevailing", "counter", "minority", "watch")
INSUFFICIENT_EVIDENCE_TEXT = "[Insufficient evidence to support this claim]"


@dataclass(frozen=True)
class ValidationReport:
    total_bullets: int
    cited_bullets: int
    removed_bullets: int
    validation_passed: bool
    should_retry: bool
    empty_core_sections: List[str]
    synthesis: Dict[str, List[Dict[str, Any]]]
    citation_store: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _sanitize_citation(raw: Mapping[str, Any]) -> Dict[str, Any]:
    citation = dict(raw)
    if citation.get("paywall_policy") == "metadata_only":
        citation.pop("quote_span", None)
    return citation


def _is_valid_citation(citation: Mapping[str, Any]) -> bool:
    return bool(citation.get("url")) and bool(citation.get("published_at"))


def _normalize_bullet(raw_bullet: Any) -> Dict[str, Any]:
    if isinstance(raw_bullet, MutableMapping):
        bullet = dict(raw_bullet)
    else:
        bullet = {"text": str(raw_bullet), "citation_ids": []}

    citation_ids = bullet.get("citation_ids", [])
    if not isinstance(citation_ids, list):
        citation_ids = []
    bullet["citation_ids"] = citation_ids
    bullet["text"] = str(bullet.get("text", ""))
    return bullet


def _extract_claim_spans(text: str) -> List[str]:
    spans = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+", text) if segment.strip()]
    return spans or [text.strip()]


def _citation_matches_source_registry(
    citation: Mapping[str, Any],
    source_registry: Mapping[str, Mapping[str, Any]] | None,
) -> bool:
    if source_registry is None:
        return True

    source_id = citation.get("source_id")
    if not source_id:
        return False

    source_meta = source_registry.get(str(source_id))
    if not source_meta:
        return False

    expected_base = source_meta.get("base_url") or source_meta.get("url")
    if not expected_base:
        return False

    citation_host = urlparse(str(citation.get("url", ""))).netloc.lower()
    expected_host = urlparse(str(expected_base)).netloc.lower()
    return bool(citation_host and expected_host and citation_host == expected_host)


def _has_claim_span_coverage(bullet: Mapping[str, Any], valid_ids: List[str]) -> bool:
    spans = _extract_claim_spans(str(bullet.get("text", "")))
    if len(spans) <= 1:
        return bool(valid_ids)

    span_citations = bullet.get("claim_span_citations")
    if not isinstance(span_citations, list) or len(span_citations) < len(spans):
        return False

    valid_set = set(valid_ids)
    for i in range(len(spans)):
        mapped = span_citations[i]
        if not isinstance(mapped, list):
            return False
        mapped_ids = [str(cid) for cid in mapped if str(cid) in valid_set]
        if not mapped_ids:
            return False
    return True


def validate_synthesis(
    synthesis: Mapping[str, Iterable[Any]],
    citation_store: Mapping[str, Mapping[str, Any]],
    *,
    source_registry: Mapping[str, Mapping[str, Any]] | None = None,
    replace_with_placeholder: bool = True,
    max_removed_without_retry: int = 3,
) -> ValidationReport:
    sanitized_store: Dict[str, Dict[str, Any]] = {
        str(cid): _sanitize_citation(citation)
        for cid, citation in citation_store.items()
    }

    normalized_synthesis: Dict[str, List[Dict[str, Any]]] = {}
    total_bullets = 0
    cited_bullets = 0
    removed_bullets = 0

    for section, raw_bullets in synthesis.items():
        section_out: List[Dict[str, Any]] = []
        for raw_bullet in list(raw_bullets):
            bullet = _normalize_bullet(raw_bullet)

            if section in CORE_SECTIONS:
                total_bullets += 1

            valid_ids: List[str] = []
            for citation_id in bullet["citation_ids"]:
                cid = str(citation_id)
                citation = sanitized_store.get(cid)
                if (
                    citation
                    and _is_valid_citation(citation)
                    and _citation_matches_source_registry(citation, source_registry)
                ):
                    valid_ids.append(cid)

            if section in CORE_SECTIONS and (
                not valid_ids or not _has_claim_span_coverage(bullet, valid_ids)
            ):
                removed_bullets += 1
                if replace_with_placeholder:
                    section_out.append(
                        {
                            **bullet,
                            "text": INSUFFICIENT_EVIDENCE_TEXT,
                            "citation_ids": [],
                            "validator_action": "replaced_insufficient_evidence",
                        }
                    )
                continue

            bullet["citation_ids"] = valid_ids
            if section in CORE_SECTIONS:
                cited_bullets += 1
            section_out.append(bullet)

        normalized_synthesis[section] = section_out

    # Ensure core sections exist in normalized output even if absent in input.
    for section in CORE_SECTIONS:
        normalized_synthesis.setdefault(section, [])

    empty_core_sections = [
        section for section in CORE_SECTIONS if len(normalized_synthesis.get(section, [])) == 0
    ]
    should_retry = removed_bullets > max_removed_without_retry or bool(empty_core_sections)
    validation_passed = not should_retry

    return ValidationReport(
        total_bullets=total_bullets,
        cited_bullets=cited_bullets,
        removed_bullets=removed_bullets,
        validation_passed=validation_passed,
        should_retry=should_retry,
        empty_core_sections=empty_core_sections,
        synthesis=deepcopy(normalized_synthesis),
        citation_store=deepcopy(sanitized_store),
    )
