from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


SECTION_SEQUENCE = ("prevailing", "counter", "minority", "watch")


def build_citation_store(
    *,
    evidence_items: Iterable[Mapping[str, Any]],
    documents_by_id: Mapping[str, Mapping[str, Any]],
    chunks_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    citations: dict[str, dict[str, Any]] = {}
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
) -> dict[str, list[dict[str, Any]]]:
    synthesis = {section: [] for section in SECTION_SEQUENCE}
    citation_ids = list(citation_store.keys())

    for index, item in enumerate(_sorted_evidence_items(evidence_items)):
        if index >= len(SECTION_SEQUENCE) or index >= len(citation_ids):
            break

        section = SECTION_SEQUENCE[index]
        doc = documents_by_id[str(item["doc_id"])]
        synthesis[section].append(
            {
                "text": _build_bullet_text(section=section, document=doc, publisher=str(item["publisher"])),
                "citation_ids": [citation_ids[index]],
                "confidence_label": _confidence_label(int(item["credibility_tier"])),
            }
        )

    return synthesis


def _sorted_evidence_items(evidence_items: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        evidence_items,
        key=lambda item: (
            int(item.get("rank_in_pack", 9999)),
            str(item.get("chunk_id", "")),
        ),
    )


def _build_bullet_text(*, section: str, document: Mapping[str, Any], publisher: str) -> str:
    title = str(document.get("title") or document.get("rss_snippet") or publisher)
    if section == "watch":
        return f"Watch {title.lower()}."
    return f"{title} ({publisher})."


def _confidence_label(credibility_tier: int) -> str:
    if credibility_tier <= 1:
        return "high"
    if credibility_tier == 2:
        return "medium"
    return "low"
