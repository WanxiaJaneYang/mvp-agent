from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any


SECTION_SEQUENCE = ("prevailing", "counter", "minority", "watch")
TOPIC_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "becomes",
    "challenge",
    "could",
    "current",
    "despite",
    "drastic",
    "extends",
    "extend",
    "focus",
    "for",
    "guidance",
    "how",
    "immediate",
    "in",
    "is",
    "keep",
    "keeps",
    "latest",
    "less",
    "long",
    "longterm",
    "longerterm",
    "may",
    "more",
    "move",
    "moves",
    "next",
    "not",
    "officials",
    "path",
    "prices",
    "rally",
    "remains",
    "response",
    "shape",
    "short",
    "shortterm",
    "smaller",
    "some",
    "soon",
    "spending",
    "steady",
    "supply",
    "term",
    "that",
    "the",
    "their",
    "traders",
    "up",
    "upside",
    "view",
    "volatility",
    "week",
    "will",
}


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
    sorted_items = _sorted_evidence_items(evidence_items)
    citations_by_item = _index_citations(citation_store)
    issues: list[dict[str, Any]] = []

    for issue_index, issue_group in enumerate(_group_items_by_issue(sorted_items, documents_by_id), start=1):
        issue_key = issue_group["issue_key"]
        issue = {
            "issue_id": f"issue_{issue_index:03d}",
            "title": _build_issue_title(issue_key),
            "summary": _build_issue_summary(issue_key),
            "prevailing": [],
            "counter": [],
            "minority": [],
            "watch": [],
        }

        for section, item in zip(SECTION_SEQUENCE, issue_group["items"]):
            citation = citations_by_item.get((str(item["doc_id"]), str(item["chunk_id"])))
            if citation is None:
                continue

            document = documents_by_id[str(item["doc_id"])]
            issue[section].append(
                {
                    "text": _build_bullet_text(section=section, document=document, publisher=str(item["publisher"])),
                    "citation_ids": [str(citation["citation_id"])],
                    "confidence_label": _confidence_label(int(item["credibility_tier"])),
                    "evidence": [_build_evidence_entry(citation)],
                }
            )

        issues.append(issue)

    return {"issues": issues}


def _sorted_evidence_items(evidence_items: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        evidence_items,
        key=lambda item: (
            int(item.get("rank_in_pack", 9999)),
            str(item.get("chunk_id", "")),
        ),
    )


def _index_citations(
    citation_store: Mapping[str, Mapping[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for citation in citation_store.values():
        indexed[(str(citation["doc_id"]), str(citation["chunk_id"]))] = dict(citation)
    return indexed


def _group_items_by_issue(
    sorted_items: list[Mapping[str, Any]],
    documents_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    token_sets: list[set[str]] = []
    token_counts: Counter[str] = Counter()
    token_first_seen: dict[str, int] = {}

    for index, item in enumerate(sorted_items):
        document = documents_by_id[str(item["doc_id"])]
        tokens = set(_topic_tokens(document))
        token_sets.append(tokens)
        for token in tokens:
            token_counts[token] += 1
            token_first_seen.setdefault(token, index)

    ranked_tokens = [
        token
        for token, count in sorted(
            token_counts.items(),
            key=lambda pair: (-pair[1], token_first_seen[pair[0]], pair[0]),
        )
        if count > 1
    ]

    groups: list[tuple[str, list[int]]] = []
    unassigned = set(range(len(sorted_items)))

    for token in ranked_tokens:
        matching = [index for index in sorted(unassigned) if token in token_sets[index]]
        if len(matching) <= 1:
            continue
        groups.append((token, matching))
        unassigned.difference_update(matching)
        if len(groups) == 3:
            break

    remaining = sorted(unassigned)
    if remaining:
        if groups and len(remaining) == 1:
            groups[0][1].extend(remaining)
        elif len(groups) < 3:
            groups.append((_fallback_issue_key(sorted_items[remaining[0]], documents_by_id), remaining))
        else:
            groups[-1][1].extend(remaining)

    if not groups and sorted_items:
        groups.append((_fallback_issue_key(sorted_items[0], documents_by_id), list(range(len(sorted_items)))))

    return [
        {
            "issue_key": issue_key,
            "items": [sorted_items[index] for index in sorted(indices)[: len(SECTION_SEQUENCE)]],
        }
        for issue_key, indices in groups
    ]


def _topic_tokens(document: Mapping[str, Any]) -> list[str]:
    text = " ".join(
        str(document.get(field, "")).lower()
        for field in ("title", "rss_snippet")
        if document.get(field)
    )
    cleaned = "".join(character if character.isalnum() else " " for character in text)
    return [token for token in cleaned.split() if len(token) > 2 and token not in TOPIC_STOPWORDS]


def _fallback_issue_key(
    item: Mapping[str, Any],
    documents_by_id: Mapping[str, Mapping[str, Any]],
) -> str:
    document = documents_by_id[str(item["doc_id"])]
    tokens = _topic_tokens(document)
    return tokens[0] if tokens else "market"


def _build_issue_title(issue_key: str) -> str:
    return f"{issue_key.capitalize()} outlook"


def _build_issue_summary(issue_key: str) -> str:
    return f"The evidence clusters around the {issue_key} outlook debate."


def _build_bullet_text(*, section: str, document: Mapping[str, Any], publisher: str) -> str:
    title = str(document.get("title") or document.get("rss_snippet") or publisher)
    if section == "watch":
        return f"Watch {title.lower()}."
    return f"{title} ({publisher})."


def _build_evidence_entry(citation: Mapping[str, Any]) -> dict[str, Any]:
    support_text = str(citation.get("quote_text") or citation.get("snippet_text") or citation.get("title") or "")
    return {
        "citation_id": str(citation["citation_id"]),
        "publisher": str(citation.get("publisher") or ""),
        "published_at": citation.get("published_at"),
        "support_text": support_text,
    }


def _confidence_label(credibility_tier: int) -> str:
    if credibility_tier <= 1:
        return "high"
    if credibility_tier == 2:
        return "medium"
    return "low"
