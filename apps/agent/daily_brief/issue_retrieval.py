from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any, cast

from apps.agent.pipeline.types import (
    BriefPlan,
    EvidencePackItem,
    IssueEvidenceCoverageSummary,
    IssueEvidenceScope,
)

OPPOSING_TERMS = ("against", "challenge", "despite", "however", "question", "push back")
MINORITY_TERMS = ("contrarian", "dissent", "few", "minority", "outlier")
WATCH_TERMS = ("ahead", "monitor", "next", "risk", "watch")


def build_brief_corpus_report(
    *,
    fts_rows: Iterable[Mapping[str, Any]],
    pack_size: int = 30,
) -> dict[str, Any]:
    rows = [_normalized_row(row) for row in fts_rows]
    if not rows or pack_size <= 0:
        return {
            "items": [],
            "diversity_check": "fail",
            "diversity_stats": _coverage_summary([], rows_by_chunk_id={}),
            "notes": ["No eligible rows were available for corpus-first retrieval."],
        }

    rows.sort(
        key=lambda row: (
            -float(row["retrieval_score"]),
            -float(row["_published_timestamp"]),
            str(row["chunk_id"]),
        )
    )
    selected = _select_diverse_rows(rows=rows, pack_size=pack_size)
    items = [_public_item(row=row, rank=index) for index, row in enumerate(selected, start=1)]
    stats = _coverage_summary(
        [item["chunk_id"] for item in items],
        rows_by_chunk_id={row["chunk_id"]: row for row in rows},
    )
    notes: list[str] = []
    if int(stats["unique_publishers"]) < 3:
        notes.append("Corpus diversity is thin; brief may need compressed render mode.")
    return {
        "items": items,
        "diversity_check": "pass" if int(stats["unique_publishers"]) >= 3 else "warn",
        "diversity_stats": stats,
        "notes": notes,
    }


def build_issue_evidence_scopes(
    *,
    brief_plan: BriefPlan,
    corpus_items: Iterable[EvidencePackItem],
    fts_rows: Iterable[Mapping[str, Any]],
    registry: Mapping[str, Mapping[str, Any]],
) -> list[IssueEvidenceScope]:
    corpus_list = list(corpus_items)
    rows_by_chunk_id = {str(row["chunk_id"]): row for row in fts_rows}
    used_chunk_ids: set[str] = set()
    scopes: list[IssueEvidenceScope] = []

    for index, seed in enumerate(brief_plan["candidate_issue_seeds"], start=1):
        scored_chunk_ids = _rank_chunks_for_seed(seed=seed, corpus_items=corpus_list, rows_by_chunk_id=rows_by_chunk_id)
        primary_chunk_ids = [chunk_id for chunk_id in scored_chunk_ids if chunk_id not in used_chunk_ids][:3]
        if not primary_chunk_ids:
            primary_chunk_ids = _unused_chunk_ids(
                corpus_items=corpus_list,
                used_chunk_ids=used_chunk_ids,
                limit=2,
            )
        used_chunk_ids.update(primary_chunk_ids)

        opposing_chunk_ids = _bucket_chunk_ids(
            chunk_ids=scored_chunk_ids,
            rows_by_chunk_id=rows_by_chunk_id,
            terms=OPPOSING_TERMS,
            used_chunk_ids=used_chunk_ids,
            limit=2,
        )
        minority_chunk_ids = _bucket_chunk_ids(
            chunk_ids=scored_chunk_ids,
            rows_by_chunk_id=rows_by_chunk_id,
            terms=MINORITY_TERMS,
            used_chunk_ids=used_chunk_ids,
            limit=2,
        )
        watch_chunk_ids = _bucket_chunk_ids(
            chunk_ids=scored_chunk_ids,
            rows_by_chunk_id=rows_by_chunk_id,
            terms=WATCH_TERMS,
            used_chunk_ids=set(),
            limit=2,
        )
        all_chunk_ids = primary_chunk_ids + opposing_chunk_ids + minority_chunk_ids + watch_chunk_ids
        scopes.append(
            IssueEvidenceScope(
                issue_id=f"issue_{index:03d}",
                issue_seed=str(seed),
                primary_chunk_ids=primary_chunk_ids,
                opposing_chunk_ids=opposing_chunk_ids,
                minority_chunk_ids=minority_chunk_ids,
                watch_chunk_ids=watch_chunk_ids,
                coverage_summary=_issue_coverage_summary(
                    chunk_ids=all_chunk_ids,
                    rows_by_chunk_id=rows_by_chunk_id,
                    registry=registry,
                ),
            )
        )
    return scopes[: max(1, int(brief_plan["issue_budget"]))]


def _normalized_row(row: Mapping[str, Any]) -> dict[str, Any]:
    published_timestamp = _published_timestamp(row.get("published_at"))
    credibility_tier = int(row.get("credibility_tier", 4) or 4)
    recency_score = 1.0 if published_timestamp > 0 else 0.4
    credibility_score = max(0.2, (5 - credibility_tier) / 4)
    token_richness = min(1.0, len(_tokens(str(row.get("text") or ""))) / 40.0)
    retrieval_score = round(recency_score * 0.45 + credibility_score * 0.35 + token_richness * 0.20, 6)
    return {
        "chunk_id": str(row["chunk_id"]),
        "doc_id": str(row["doc_id"]),
        "source_id": str(row["source_id"]),
        "publisher": str(row["publisher"]),
        "credibility_tier": credibility_tier,
        "retrieval_score": retrieval_score,
        "semantic_score": round(token_richness, 6),
        "recency_score": recency_score,
        "credibility_score": credibility_score,
        "_published_timestamp": published_timestamp,
    }


def _select_diverse_rows(*, rows: list[dict[str, Any]], pack_size: int) -> list[dict[str, Any]]:
    publisher_limit = max(1, int(math.ceil(min(pack_size, len(rows)) * 0.4)))
    selected: list[dict[str, Any]] = []
    publisher_counts: Counter[str] = Counter()
    for row in rows:
        if len(selected) >= pack_size:
            break
        if publisher_counts[str(row["publisher"])] >= publisher_limit:
            continue
        selected.append(row)
        publisher_counts[str(row["publisher"])] += 1
    for row in rows:
        if len(selected) >= pack_size:
            break
        if row in selected:
            continue
        selected.append(row)
    return selected


def _public_item(*, row: Mapping[str, Any], rank: int) -> EvidencePackItem:
    return cast(
        EvidencePackItem,
        {
            "chunk_id": row["chunk_id"],
            "source_id": row["source_id"],
            "publisher": row["publisher"],
            "credibility_tier": row["credibility_tier"],
            "retrieval_score": row["retrieval_score"],
            "semantic_score": row["semantic_score"],
            "recency_score": row["recency_score"],
            "credibility_score": row["credibility_score"],
            "rank_in_pack": rank,
            "doc_id": row["doc_id"],
        },
    )


def _rank_chunks_for_seed(
    *,
    seed: str,
    corpus_items: Iterable[EvidencePackItem],
    rows_by_chunk_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    seed_tokens = set(_tokens(seed))
    scored: list[tuple[float, str]] = []
    for item in corpus_items:
        chunk_id = str(item["chunk_id"])
        row = rows_by_chunk_id.get(chunk_id)
        text = str(row.get("text") if isinstance(row, Mapping) else "")
        text_tokens = set(_tokens(text))
        overlap = len(seed_tokens & text_tokens)
        score = overlap * 1.0 + float(item.get("semantic_score") or 0.0) + float(item.get("retrieval_score") or 0.0)
        scored.append((score, chunk_id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [chunk_id for _score, chunk_id in scored]


def _bucket_chunk_ids(
    *,
    chunk_ids: Iterable[str],
    rows_by_chunk_id: Mapping[str, Mapping[str, Any]],
    terms: tuple[str, ...],
    used_chunk_ids: set[str],
    limit: int,
) -> list[str]:
    bucket: list[str] = []
    for chunk_id in chunk_ids:
        if chunk_id in used_chunk_ids:
            continue
        row = rows_by_chunk_id.get(chunk_id)
        text = str(row.get("text") if isinstance(row, Mapping) else "").lower()
        if not any(term in text for term in terms):
            continue
        bucket.append(chunk_id)
        if len(bucket) >= limit:
            break
    return bucket


def _unused_chunk_ids(
    *,
    corpus_items: Iterable[EvidencePackItem],
    used_chunk_ids: set[str],
    limit: int,
) -> list[str]:
    unused: list[str] = []
    for item in corpus_items:
        chunk_id = str(item["chunk_id"])
        if chunk_id in used_chunk_ids or chunk_id in unused:
            continue
        unused.append(chunk_id)
        if len(unused) >= limit:
            break
    return unused


def _issue_coverage_summary(
    *,
    chunk_ids: Iterable[str],
    rows_by_chunk_id: Mapping[str, Mapping[str, Any]],
    registry: Mapping[str, Mapping[str, Any]],
) -> IssueEvidenceCoverageSummary:
    rows = [rows_by_chunk_id[chunk_id] for chunk_id in chunk_ids if chunk_id in rows_by_chunk_id]
    source_roles: set[str] = set()
    publishers: set[str] = set()
    timestamps: list[float] = []
    for row in rows:
        source_id = str(row.get("source_id") or "")
        publishers.add(str(row.get("publisher") or ""))
        timestamps.append(_published_timestamp(row.get("published_at")))
        registry_entry = registry.get(source_id, {})
        tags = registry_entry.get("tags", []) if isinstance(registry_entry, Mapping) else []
        for tag in tags:
            if isinstance(tag, str):
                source_roles.add(_source_role(tag))
    nonzero_timestamps = [timestamp for timestamp in timestamps if timestamp > 0]
    time_span_hours = 0
    if nonzero_timestamps:
        time_span_hours = int(round((max(nonzero_timestamps) - min(nonzero_timestamps)) / 3600))
    return {
        "unique_publishers": len([publisher for publisher in publishers if publisher]),
        "source_roles": sorted(source_roles),
        "time_span_hours": time_span_hours,
    }


def _coverage_summary(
    chunk_ids: Iterable[str],
    *,
    rows_by_chunk_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [rows_by_chunk_id[chunk_id] for chunk_id in chunk_ids if chunk_id in rows_by_chunk_id]
    publishers = {str(row.get("publisher") or "") for row in rows if row.get("publisher")}
    tier_counts = Counter(int(row.get("credibility_tier", 4) or 4) for row in rows)
    total = len(rows)
    return {
        "selected_count": total,
        "unique_publishers": len(publishers),
        "tier_1_pct": round((tier_counts[1] / total) * 100, 2) if total else 0.0,
        "tier_2_pct": round((tier_counts[2] / total) * 100, 2) if total else 0.0,
        "tier_3_pct": round((tier_counts[3] / total) * 100, 2) if total else 0.0,
        "tier_4_pct": round((tier_counts[4] / total) * 100, 2) if total else 0.0,
        "tier_1_2_pct": round(((tier_counts[1] + tier_counts[2]) / total) * 100, 2) if total else 0.0,
        "max_publisher_pct": round(
            (max(Counter(str(row.get("publisher") or "") for row in rows).values()) / total) * 100,
            2,
        )
        if total
        else 0.0,
    }


def _source_role(tag: str) -> str:
    if tag.startswith("policy_") or tag.startswith("macro_"):
        return "official"
    if "market" in tag:
        return "market_media"
    return tag


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def _published_timestamp(value: Any) -> float:
    if not isinstance(value, str) or not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0
