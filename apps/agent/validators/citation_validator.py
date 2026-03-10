from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import re
from typing import Any, Collection, Dict, Iterable, List, Mapping
from urllib.parse import urlparse

CORE_SECTIONS = ("prevailing", "counter", "minority", "watch")
INSUFFICIENT_EVIDENCE_TEXT = "[Insufficient evidence to support this claim]"
NUMERIC_TIME_PATTERN = re.compile(
    r"\b(?:\d+(?:\.\d+)?%?|\d{4}-\d{2}-\d{2}|q[1-4]|"
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
    re.IGNORECASE,
)
POLICY_OR_MACRO_PATTERN = re.compile(
    r"\b(?:fed|federal reserve|ecb|bank of england|bank of japan|"
    r"people's bank|pboc|monetary authority|reserve bank|hkma|"
    r"rates?|policy settings|policy rate|cpi|inflation|payroll|employment|"
    r"unemployment|gdp|consumer spending|personal income|ppi|retail sales)\b",
    re.IGNORECASE,
)
OFFICIAL_POLICY_TAGS = frozenset({"policy_centralbank", "macro_data"})


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
    legacy_id = citation.pop("id", None)
    if legacy_id is not None and "citation_id" not in citation:
        citation["citation_id"] = str(legacy_id)

    quote_span = citation.pop("quote_span", None)
    if "quote_text" not in citation and isinstance(quote_span, Mapping):
        quote_text = quote_span.get("text")
        citation["quote_text"] = None if quote_text is None else str(quote_text)

    snippet_span = citation.pop("snippet_span", None)
    if "snippet_text" not in citation and isinstance(snippet_span, Mapping):
        citation["snippet_text"] = str(snippet_span.get("text") or "")

    if citation.get("paywall_policy") == "metadata_only":
        citation["quote_text"] = None
    elif "quote_text" in citation and citation["quote_text"] is not None:
        citation["quote_text"] = str(citation["quote_text"])
    else:
        citation.setdefault("quote_text", None)

    if "snippet_text" in citation and citation["snippet_text"] is not None:
        citation["snippet_text"] = str(citation["snippet_text"])
    else:
        citation["snippet_text"] = str(citation.get("title") or "")
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


def _citation_quality_meta(
    citation: Mapping[str, Any],
    source_registry: Mapping[str, Mapping[str, Any]] | None,
) -> Dict[str, Any]:
    source_id = str(citation.get("source_id") or "")
    publisher = str(citation.get("publisher") or "")
    if source_registry is None or not source_id:
        return {
            "has_registry_meta": False,
            "source_id": source_id,
            "publisher": publisher,
            "credibility_tier": None,
            "tags": [],
        }

    source_meta = source_registry.get(source_id)
    if not isinstance(source_meta, Mapping):
        return {
            "has_registry_meta": False,
            "source_id": source_id,
            "publisher": publisher,
            "credibility_tier": None,
            "tags": [],
        }

    raw_tier = source_meta.get("credibility_tier")
    credibility_tier = None
    if raw_tier is not None:
        try:
            credibility_tier = int(raw_tier)
        except (TypeError, ValueError):
            credibility_tier = None

    raw_tags = source_meta.get("tags", [])
    tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []
    return {
        "has_registry_meta": True,
        "source_id": source_id,
        "publisher": publisher,
        "credibility_tier": credibility_tier,
        "tags": tags,
    }


def _passes_numeric_time_quality(
    *,
    text: str,
    cited_citations: List[Mapping[str, Any]],
    source_registry: Mapping[str, Mapping[str, Any]] | None,
) -> bool:
    if source_registry is None or not NUMERIC_TIME_PATTERN.search(text):
        return True

    cited_meta = [_citation_quality_meta(citation, source_registry) for citation in cited_citations]
    if not any(meta["has_registry_meta"] for meta in cited_meta):
        return True

    if any(meta["credibility_tier"] == 1 for meta in cited_meta):
        return True

    independence_keys = {
        meta["source_id"] or meta["publisher"]
        for meta in cited_meta
        if meta["source_id"] or meta["publisher"]
    }
    return len(independence_keys) >= 2


def _official_policy_source_available(
    *,
    available_source_ids: Collection[str] | None,
    source_registry: Mapping[str, Mapping[str, Any]] | None,
) -> bool:
    if source_registry is None:
        return False

    if available_source_ids is None:
        return False

    for source_id in available_source_ids:
        source_meta = source_registry.get(str(source_id))
        if not isinstance(source_meta, Mapping):
            continue
        raw_tier = source_meta.get("credibility_tier")
        try:
            credibility_tier = int(raw_tier) if raw_tier is not None else None
        except (TypeError, ValueError):
            credibility_tier = None
        raw_tags = source_meta.get("tags", [])
        tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []
        if credibility_tier == 1 and OFFICIAL_POLICY_TAGS.intersection(tags):
            return True
    return False


def _passes_policy_claim_quality(
    *,
    text: str,
    cited_citations: List[Mapping[str, Any]],
    available_source_ids: Collection[str] | None,
    source_registry: Mapping[str, Mapping[str, Any]] | None,
) -> bool:
    if source_registry is None or not POLICY_OR_MACRO_PATTERN.search(text):
        return True
    if not _official_policy_source_available(
        available_source_ids=available_source_ids,
        source_registry=source_registry,
    ):
        return True

    cited_meta = [_citation_quality_meta(citation, source_registry) for citation in cited_citations]
    if not any(meta["has_registry_meta"] for meta in cited_meta):
        return True

    return any(meta["credibility_tier"] == 1 for meta in cited_meta)


def _passes_quality_rules(
    *,
    bullet: Mapping[str, Any],
    valid_ids: List[str],
    citation_store: Mapping[str, Mapping[str, Any]],
    available_source_ids: Collection[str] | None,
    source_registry: Mapping[str, Mapping[str, Any]] | None,
) -> bool:
    if source_registry is None:
        return True

    cited_citations = [citation_store[citation_id] for citation_id in valid_ids if citation_id in citation_store]
    text = str(bullet.get("text", ""))
    return _passes_numeric_time_quality(
        text=text,
        cited_citations=cited_citations,
        source_registry=source_registry,
    ) and _passes_policy_claim_quality(
        text=text,
        cited_citations=cited_citations,
        available_source_ids=available_source_ids,
        source_registry=source_registry,
    )


def validate_synthesis(
    synthesis: Mapping[str, Iterable[Any]],
    citation_store: Mapping[str, Mapping[str, Any]],
    *,
    source_registry: Mapping[str, Mapping[str, Any]] | None = None,
    available_source_ids: Collection[str] | None = None,
    replace_with_placeholder: bool = True,
    max_removed_without_retry: int = 3,
) -> ValidationReport:
    sanitized_store: Dict[str, Dict[str, Any]] = {}
    for cid, citation in citation_store.items():
        normalized_citation = _sanitize_citation(citation)
        normalized_citation["citation_id"] = str(normalized_citation.get("citation_id") or cid)
        sanitized_store[str(cid)] = normalized_citation

    normalized_synthesis: Dict[str, Any] = {}
    total_bullets = 0
    cited_bullets = 0
    removed_bullets = 0

    for section, raw_bullets in synthesis.items():
        if section not in CORE_SECTIONS:
            normalized_synthesis[section] = deepcopy(raw_bullets)
            continue

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

            if (
                not valid_ids
                or not _has_claim_span_coverage(bullet, valid_ids)
                or not _passes_quality_rules(
                    bullet=bullet,
                    valid_ids=valid_ids,
                    citation_store=sanitized_store,
                    available_source_ids=available_source_ids,
                    source_registry=source_registry,
                )
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
            cited_bullets += 1
            section_out.append(bullet)

        normalized_synthesis[section] = section_out

    # Ensure core sections exist in normalized output even if absent in input.
    for section in CORE_SECTIONS:
        normalized_synthesis.setdefault(section, [])

    empty_core_sections: List[str] = []
    for section in CORE_SECTIONS:
        section_bullets = normalized_synthesis.get(section, [])
        if len(section_bullets) == 0:
            empty_core_sections.append(section)
            continue
        if all(isinstance(b, Mapping) and _is_placeholder_bullet(b) for b in section_bullets):
            empty_core_sections.append(section)
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
