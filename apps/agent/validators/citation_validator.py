from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, Iterable, List, Mapping
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
    synthesis: Dict[str, Any]
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
    if isinstance(raw_bullet, Mapping):
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
    """
    Split a bullet into approximate claim spans.

    Heuristic-only splitter: sentence punctuation + newline boundaries.
    Known limitations include abbreviations, decimals, and ellipses.
    """
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
        # If no source_id is available, skip registry-based URL matching.
        return True

    source_meta = source_registry.get(str(source_id))
    if not source_meta:
        return False

    expected_base = source_meta.get("base_url") or source_meta.get("url")
    if not expected_base:
        return False

    citation_parsed = urlparse(str(citation.get("url", "")))
    expected_parsed = urlparse(str(expected_base))

    citation_host = (citation_parsed.hostname or "").lower()
    expected_host = (expected_parsed.hostname or "").lower()
    if not citation_host or not expected_host:
        return False

    host_matches = citation_host == expected_host or citation_host.endswith("." + expected_host)
    expected_scheme = (expected_parsed.scheme or "").lower()
    citation_scheme = (citation_parsed.scheme or "").lower()
    scheme_matches = not expected_scheme or expected_scheme == citation_scheme
    return bool(host_matches and scheme_matches)


def _has_claim_span_coverage(bullet: Mapping[str, Any], valid_ids: List[str]) -> bool:
    spans = _extract_claim_spans(str(bullet.get("text", "")))
    if len(spans) <= 1:
        return bool(valid_ids)

    span_citations = bullet.get("claim_span_citations")
    # Allow shared citation groups across a multi-sentence span (contract 3.2B).
    if span_citations is None:
        return bool(valid_ids)

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


def _is_placeholder_bullet(bullet: Mapping[str, Any]) -> bool:
    return str(bullet.get("text", "")) == INSUFFICIENT_EVIDENCE_TEXT


def _validate_core_sections(
    sections: Mapping[str, Iterable[Any]],
    *,
    sanitized_store: Mapping[str, Mapping[str, Any]],
    source_registry: Mapping[str, Mapping[str, Any]] | None,
    replace_with_placeholder: bool,
    section_prefix: str = "",
) -> tuple[Dict[str, List[Dict[str, Any]]], int, int, int, List[str]]:
    normalized_sections: Dict[str, List[Dict[str, Any]]] = {}
    total_bullets = 0
    cited_bullets = 0
    removed_bullets = 0

    for section in CORE_SECTIONS:
        raw_bullets = sections.get(section, [])
        section_out: List[Dict[str, Any]] = []

        for raw_bullet in raw_bullets:
            bullet = _normalize_bullet(raw_bullet)
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

            if not valid_ids or not _has_claim_span_coverage(bullet, valid_ids):
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
            cited_bullets += 1
            section_out.append(bullet)

        normalized_sections[section] = section_out

    empty_core_sections: List[str] = []
    for section in CORE_SECTIONS:
        section_bullets = normalized_sections[section]
        qualified_name = f"{section_prefix}{section}"
        if len(section_bullets) == 0:
            empty_core_sections.append(qualified_name)
            continue
        if all(isinstance(b, Mapping) and _is_placeholder_bullet(b) for b in section_bullets):
            empty_core_sections.append(qualified_name)

    return normalized_sections, total_bullets, cited_bullets, removed_bullets, empty_core_sections


def validate_synthesis(
    synthesis: Mapping[str, Any],
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

    normalized_synthesis: Dict[str, Any] = {}
    total_bullets = 0
    cited_bullets = 0
    removed_bullets = 0
    empty_core_sections: List[str] = []

    if isinstance(synthesis.get("issues"), list):
        normalized_synthesis = {
            key: deepcopy(value)
            for key, value in synthesis.items()
            if key != "issues"
        }
        normalized_issues: List[Dict[str, Any]] = []
        issue_items = synthesis["issues"]
        for index, raw_issue in enumerate(issue_items, start=1):
            issue = dict(raw_issue) if isinstance(raw_issue, Mapping) else {"value": deepcopy(raw_issue)}
            issue_id = str(issue.get("issue_id") or f"issue_{index:03d}")
            normalized_sections, issue_total, issue_cited, issue_removed, issue_empty = _validate_core_sections(
                issue,
                sanitized_store=sanitized_store,
                source_registry=source_registry,
                replace_with_placeholder=replace_with_placeholder,
                section_prefix=f"{issue_id}.",
            )
            issue.update(normalized_sections)
            normalized_issues.append(issue)
            total_bullets += issue_total
            cited_bullets += issue_cited
            removed_bullets += issue_removed
            empty_core_sections.extend(issue_empty)

        normalized_synthesis["issues"] = normalized_issues
        if len(issue_items) == 0:
            empty_core_sections.append("issues")
    else:
        for section, raw_value in synthesis.items():
            if section not in CORE_SECTIONS:
                normalized_synthesis[section] = deepcopy(raw_value)

        normalized_sections, total_bullets, cited_bullets, removed_bullets, empty_core_sections = (
            _validate_core_sections(
                synthesis,
                sanitized_store=sanitized_store,
                source_registry=source_registry,
                replace_with_placeholder=replace_with_placeholder,
            )
        )
        normalized_synthesis.update(normalized_sections)

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
