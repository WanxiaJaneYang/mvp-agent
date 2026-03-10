from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Mapping
from typing import Any

from apps.agent.pipeline.types import (
    DAILY_BRIEF_CORE_OUTPUT_SECTIONS,
    CitationStoreEntry,
    DailyBriefBullet,
    DailyBriefOutputSection,
    DailyBriefSynthesis,
)


WATCH_KEYWORDS = (
    "ahead",
    "could",
    "if ",
    "monitor",
    "next",
    "risk",
    "watch",
)
COUNTER_KEYWORDS = (
    "against",
    "challenge",
    "contrary",
    "doubt",
    "however",
    "push back",
    "question",
    "skeptic",
)
MINORITY_KEYWORDS = (
    "contrarian",
    "dissent",
    "few",
    "minority",
    "outlier",
)


@dataclass(frozen=True)
class _SectionCandidate:
    chunk_id: str
    item: Mapping[str, Any]
    document: Mapping[str, Any]
    citation_id: str
    scores: dict[DailyBriefOutputSection, int]


def build_citation_store(
    *,
    evidence_items: Iterable[Mapping[str, Any]],
    documents_by_id: Mapping[str, Mapping[str, Any]],
    chunks_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, CitationStoreEntry]:
    citations: dict[str, CitationStoreEntry] = {}
    for index, item in enumerate(_sorted_evidence_items(evidence_items), start=1):
        doc = documents_by_id[str(item["doc_id"])]
        chunk = chunks_by_id[str(item["chunk_id"])]
        citation_id = f"cite_{index:03d}"
        paywall_policy = str(doc["paywall_policy"])
        snippet_text = str(doc.get("rss_snippet") or doc.get("title") or chunk.get("text") or "")

        citations[citation_id] = {
            "citation_id": citation_id,
            "source_id": item["source_id"],
            "publisher": item["publisher"],
            "doc_id": item["doc_id"],
            "chunk_id": item["chunk_id"],
            "url": doc["canonical_url"],
            "title": doc.get("title"),
            "published_at": doc.get("published_at"),
            "fetched_at": doc.get("fetched_at"),
            "paywall_policy": paywall_policy,
            "quote_text": None if paywall_policy == "metadata_only" else str(chunk.get("text") or ""),
            "snippet_text": snippet_text,
        }
    return citations


def build_synthesis(
    *,
    evidence_items: Iterable[Mapping[str, Any]],
    documents_by_id: Mapping[str, Mapping[str, Any]],
    citation_store: Mapping[str, Mapping[str, Any]],
) -> DailyBriefSynthesis:
    synthesis = {section: [] for section in DAILY_BRIEF_CORE_OUTPUT_SECTIONS}
    candidates = _build_section_candidates(
        evidence_items=evidence_items,
        documents_by_id=documents_by_id,
        citation_store=citation_store,
    )
    assignments = _assign_sections(candidates)

    for section in DAILY_BRIEF_CORE_OUTPUT_SECTIONS:
        candidate = assignments.get(section)
        if candidate is None:
            continue
        bullet: DailyBriefBullet = {
            "text": _build_bullet_text(
                section=section,
                document=candidate.document,
                publisher=str(candidate.item["publisher"]),
            ),
            "citation_ids": [candidate.citation_id],
            "confidence_label": _confidence_label(int(candidate.item["credibility_tier"])),
        }
        synthesis[section].append(dict(bullet))
    return synthesis


def _sorted_evidence_items(evidence_items: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        evidence_items,
        key=lambda item: (
            int(item.get("rank_in_pack", 9999)),
            str(item.get("chunk_id", "")),
        ),
    )


def _build_section_candidates(
    *,
    evidence_items: Iterable[Mapping[str, Any]],
    documents_by_id: Mapping[str, Mapping[str, Any]],
    citation_store: Mapping[str, Mapping[str, Any]],
) -> list[_SectionCandidate]:
    citation_ids_by_chunk_id = {
        str(entry["chunk_id"]): str(citation_id)
        for citation_id, entry in citation_store.items()
        if isinstance(entry, Mapping) and entry.get("chunk_id") is not None
    }
    candidates: list[_SectionCandidate] = []
    for item in _sorted_evidence_items(evidence_items):
        chunk_id = str(item["chunk_id"])
        citation_id = citation_ids_by_chunk_id.get(chunk_id)
        if citation_id is None:
            continue
        document = documents_by_id[str(item["doc_id"])]
        candidates.append(
            _SectionCandidate(
                chunk_id=chunk_id,
                item=item,
                document=document,
                citation_id=citation_id,
                scores=_section_scores(item=item, document=document),
            )
        )
    return candidates


def _assign_sections(
    candidates: Iterable[_SectionCandidate],
) -> dict[DailyBriefOutputSection, _SectionCandidate]:
    ordered_candidates = list(candidates)
    best_assignment: dict[DailyBriefOutputSection, _SectionCandidate] = {}
    best_key: tuple[int, tuple[tuple[int, int, str], ...]] | None = None
    search_order: tuple[DailyBriefOutputSection, ...] = ("watch", "counter", "minority", "prevailing")

    def search(
        section_index: int,
        used_chunk_ids: frozenset[str],
        assignment: dict[DailyBriefOutputSection, _SectionCandidate],
    ) -> None:
        nonlocal best_assignment, best_key
        if section_index >= len(search_order):
            ranking = _assignment_key(assignment=assignment, search_order=search_order)
            if best_key is None or ranking > best_key:
                best_key = ranking
                best_assignment = dict(assignment)
            return

        section = search_order[section_index]
        assigned_any = False
        for candidate in ordered_candidates:
            if candidate.chunk_id in used_chunk_ids:
                continue
            assigned_any = True
            assignment[section] = candidate
            search(
                section_index + 1,
                used_chunk_ids | {candidate.chunk_id},
                assignment,
            )
            assignment.pop(section, None)

        if not assigned_any:
            search(section_index + 1, used_chunk_ids, assignment)

    search(0, frozenset(), {})
    return best_assignment


def _assignment_key(
    *,
    assignment: Mapping[DailyBriefOutputSection, _SectionCandidate],
    search_order: tuple[DailyBriefOutputSection, ...],
) -> tuple[int, tuple[tuple[int, int, str], ...]]:
    total_score = 0
    tie_breakers: list[tuple[int, int, str]] = []
    for section in search_order:
        candidate = assignment.get(section)
        if candidate is None:
            tie_breakers.append((-1, -9999, ""))
            continue
        score = candidate.scores[section]
        rank_in_pack = int(candidate.item.get("rank_in_pack", 9999))
        total_score += score
        tie_breakers.append((score, -rank_in_pack, candidate.chunk_id))
    return total_score, tuple(tie_breakers)


def _section_scores(
    *,
    item: Mapping[str, Any],
    document: Mapping[str, Any],
) -> dict[DailyBriefOutputSection, int]:
    text = _normalized_document_text(document)
    credibility_tier = int(item.get("credibility_tier", 4))
    rank_in_pack = int(item.get("rank_in_pack", 9999))
    rank_bonus = max(0, 50 - rank_in_pack)
    credibility_bonus = max(0, 5 - credibility_tier) * 8
    lower_consensus_bonus = max(0, credibility_tier - 1) * 8
    watch_hits = _keyword_hits(text, WATCH_KEYWORDS)
    counter_hits = _keyword_hits(text, COUNTER_KEYWORDS)
    minority_hits = _keyword_hits(text, MINORITY_KEYWORDS)
    recency_bonus = _recency_bonus(document)

    return {
        "prevailing": 90 + credibility_bonus + rank_bonus - (watch_hits + counter_hits + minority_hits) * 20,
        "counter": 20 + counter_hits * 70 + credibility_bonus + rank_bonus // 2 - watch_hits * 10,
        "minority": 15 + minority_hits * 70 + lower_consensus_bonus + rank_bonus // 3,
        "watch": 20 + watch_hits * 70 + recency_bonus + rank_bonus // 4,
        "changed": 0,
    }


def _normalized_document_text(document: Mapping[str, Any]) -> str:
    return " ".join(
        str(document.get(field, "")).lower()
        for field in ("title", "rss_snippet", "doc_type")
        if document.get(field)
    )


def _keyword_hits(text: str, keywords: Iterable[str]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _recency_bonus(document: Mapping[str, Any]) -> int:
    timestamp = str(document.get("published_at") or document.get("fetched_at") or "")
    digits = "".join(character for character in timestamp if character.isdigit())
    if len(digits) < 6:
        return 0
    hhmmss = digits[-6:]
    hours = int(hhmmss[:2])
    minutes = int(hhmmss[2:4])
    return hours * 2 + minutes // 15


def _build_bullet_text(*, section: str, document: Mapping[str, Any], publisher: str) -> str:
    title = str(document.get("title") or document.get("rss_snippet") or publisher).strip()
    normalized_title = title.rstrip(".")
    if section == "watch":
        if normalized_title.lower().startswith("watch "):
            return f"{normalized_title}."
        return f"Watch {normalized_title.lower()}."
    return f"{normalized_title} ({publisher})."


def _confidence_label(credibility_tier: int) -> str:
    if credibility_tier <= 1:
        return "high"
    if credibility_tier == 2:
        return "medium"
    return "low"
