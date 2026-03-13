from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from apps.agent.retrieval.fts_index import FTS_TABLE_NAME, search_persisted_fts_rows


def build_evidence_pack(
    *,
    fts_rows: Iterable[Mapping[str, Any]],
    query_text: str,
    pack_size: int = 30,
) -> list[dict[str, Any]]:
    return build_evidence_pack_report(
        fts_rows=fts_rows,
        query_text=query_text,
        pack_size=pack_size,
    )["items"]


def build_evidence_pack_report(
    *,
    fts_rows: Iterable[Mapping[str, Any]],
    query_text: str,
    pack_size: int = 30,
) -> dict[str, Any]:
    query_terms = _tokenize(query_text)
    if not query_terms or pack_size <= 0:
        return {
            "items": [],
            "diversity_check": "fail",
            "diversity_stats": _diversity_stats([]),
            "notes": ["No matching evidence rows were available for evidence-pack construction."],
        }

    matching_rows = _matching_rows(fts_rows=fts_rows, query_terms=query_terms)
    if not matching_rows:
        return {
            "items": [],
            "diversity_check": "fail",
            "diversity_stats": _diversity_stats([]),
            "notes": ["No rows matched the evidence-pack query terms."],
        }

    published_timestamps = [row["published_timestamp"] for row in matching_rows]
    oldest_timestamp = min(published_timestamps, default=0.0)
    newest_timestamp = max(published_timestamps, default=0.0)

    scored_rows = _score_rows(
        matching_rows=matching_rows,
        oldest_timestamp=oldest_timestamp,
        newest_timestamp=newest_timestamp,
    )
    scored_rows.sort(
        key=lambda row: (
            -float(row["retrieval_score"]),
            -float(row["_published_timestamp"]),
            str(row["chunk_id"]),
        )
    )

    selected_rows = _select_diverse_rows(scored_rows=scored_rows, pack_size=pack_size)
    pack_rows = [
        _public_row(row=row, rank=index) for index, row in enumerate(selected_rows, start=1)
    ]
    diversity_stats = _diversity_stats(pack_rows)
    violations = _diversity_violations(diversity_stats=diversity_stats)
    notes = _diversity_notes(
        violations=violations,
        target_size=min(pack_size, len(scored_rows)),
        actual_size=len(pack_rows),
    )
    return {
        "items": pack_rows,
        "diversity_check": _diversity_level(violations=violations, items=pack_rows),
        "diversity_stats": diversity_stats,
        "notes": notes,
    }


def build_persistent_hybrid_evidence_pack_report(
    *,
    connection: sqlite3.Connection,
    query_text: str,
    pack_size: int = 30,
    search_limit: int | None = None,
) -> dict[str, Any]:
    effective_search_limit = search_limit or max(pack_size * 4, pack_size)
    lexical_rows = search_persisted_fts_rows(
        connection=connection,
        query_text=query_text,
        limit=effective_search_limit,
    )
    semantic_rows = _load_top_semantic_rows(
        connection=connection,
        limit=effective_search_limit,
    )
    persisted_rows = _merge_hybrid_candidate_rows(
        lexical_rows=lexical_rows,
        semantic_rows=semantic_rows,
    )
    return build_evidence_pack_report(
        fts_rows=persisted_rows,
        query_text=query_text,
        pack_size=pack_size,
    )


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def _keyword_score(*, text: str, query_terms: list[str]) -> float:
    tokens = _tokenize(text)
    return float(sum(tokens.count(term) for term in query_terms))


def _matching_rows(
    *, fts_rows: Iterable[Mapping[str, Any]], query_terms: list[str]
) -> list[dict[str, Any]]:
    matching_rows: list[dict[str, Any]] = []
    for row in fts_rows:
        _validate_row(row)
        lexical_score = row.get("lexical_score")
        uses_precomputed_lexical = lexical_score not in (None, "")
        keyword_score = (
            float(lexical_score)
            if uses_precomputed_lexical
            else _keyword_score(text=str(row["text"]), query_terms=query_terms)
        )
        if not uses_precomputed_lexical and keyword_score <= 0:
            continue
        matching_rows.append(
            {
                "row": row,
                "keyword_score": keyword_score,
                "published_timestamp": _published_timestamp(row),
            }
        )
    return matching_rows


def _score_rows(
    *,
    matching_rows: Iterable[Mapping[str, Any]],
    oldest_timestamp: float,
    newest_timestamp: float,
) -> list[dict[str, Any]]:
    scored_rows: list[dict[str, Any]] = []
    for match in matching_rows:
        row = match["row"]
        recency_score = _recency_score(
            published_timestamp=float(match["published_timestamp"]),
            oldest_timestamp=oldest_timestamp,
            newest_timestamp=newest_timestamp,
        )
        credibility_score = _credibility_score(int(row["credibility_tier"]))
        semantic_score = _normalized_optional_score(row.get("semantic_score"))
        if row.get("lexical_score") not in (None, ""):
            retrieval_score = round(
                float(match["keyword_score"]) * 0.35
                + semantic_score * 0.45
                + recency_score * 0.10
                + credibility_score * 0.10,
                6,
            )
            public_semantic_score: float | None = semantic_score
        else:
            retrieval_score = round(
                float(match["keyword_score"]) * 0.5 + recency_score * 0.3 + credibility_score * 0.2,
                6,
            )
            public_semantic_score = None
        scored_rows.append(
            {
                "chunk_id": row["chunk_id"],
                "source_id": row["source_id"],
                "publisher": row["publisher"],
                "credibility_tier": row["credibility_tier"],
                "retrieval_score": retrieval_score,
                "semantic_score": public_semantic_score,
                "recency_score": recency_score,
                "credibility_score": credibility_score,
                "_published_timestamp": match["published_timestamp"],
            }
        )
    return scored_rows


def _select_diverse_rows(
    *, scored_rows: list[dict[str, Any]], pack_size: int
) -> list[dict[str, Any]]:
    target_size = min(pack_size, len(scored_rows))
    if target_size <= 0:
        return []

    publisher_limit = max(1, int(math.floor(target_size * 0.4)))
    tier4_limit = int(math.floor(target_size * 0.15))
    min_high_tier = int(math.ceil(target_size * 0.5))

    selected: list[dict[str, Any]] = []
    publisher_counts: Counter[str] = Counter()
    tier4_count = 0

    def can_add(row: Mapping[str, Any]) -> bool:
        publisher = str(row["publisher"])
        if publisher_counts[publisher] >= publisher_limit:
            return False
        if int(row["credibility_tier"]) == 4 and tier4_count >= tier4_limit:
            return False
        return True

    for row in scored_rows:
        if len(selected) >= target_size:
            break
        if int(row["credibility_tier"]) > 2:
            continue
        if not can_add(row):
            continue
        selected.append(row)
        publisher_counts[str(row["publisher"])] += 1
        if int(row["credibility_tier"]) == 4:
            tier4_count += 1
        if sum(1 for item in selected if int(item["credibility_tier"]) <= 2) >= min_high_tier:
            break

    for row in scored_rows:
        if len(selected) >= target_size:
            break
        if row in selected:
            continue
        if not can_add(row):
            continue
        selected.append(row)
        publisher_counts[str(row["publisher"])] += 1
        if int(row["credibility_tier"]) == 4:
            tier4_count += 1

    for row in scored_rows:
        if len(selected) >= target_size:
            break
        if row in selected:
            continue
        selected.append(row)

    return selected


def _public_row(*, row: Mapping[str, Any], rank: int) -> dict[str, Any]:
    return {
        "chunk_id": row["chunk_id"],
        "source_id": row["source_id"],
        "publisher": row["publisher"],
        "credibility_tier": row["credibility_tier"],
        "retrieval_score": row["retrieval_score"],
        "semantic_score": row["semantic_score"],
        "recency_score": row["recency_score"],
        "credibility_score": row["credibility_score"],
        "rank_in_pack": rank,
    }


def _diversity_stats(items: Iterable[Mapping[str, Any]]) -> dict[str, float | int]:
    rows = list(items)
    total = len(rows)
    if total == 0:
        return {
            "selected_count": 0,
            "unique_publishers": 0,
            "tier_1_pct": 0.0,
            "tier_2_pct": 0.0,
            "tier_3_pct": 0.0,
            "tier_4_pct": 0.0,
            "tier_1_2_pct": 0.0,
            "max_publisher_pct": 0.0,
        }

    publisher_counts = Counter(str(item["publisher"]) for item in rows)
    tier_counts = Counter(int(item["credibility_tier"]) for item in rows)
    return {
        "selected_count": total,
        "unique_publishers": len(publisher_counts),
        "tier_1_pct": round(tier_counts[1] / total * 100, 2),
        "tier_2_pct": round(tier_counts[2] / total * 100, 2),
        "tier_3_pct": round(tier_counts[3] / total * 100, 2),
        "tier_4_pct": round(tier_counts[4] / total * 100, 2),
        "tier_1_2_pct": round((tier_counts[1] + tier_counts[2]) / total * 100, 2),
        "max_publisher_pct": round(max(publisher_counts.values()) / total * 100, 2),
    }


def _diversity_violations(*, diversity_stats: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    if float(diversity_stats["max_publisher_pct"]) > 40.0:
        violations.append("publisher_dominance")
    if float(diversity_stats["tier_1_2_pct"]) < 50.0:
        violations.append("tier_1_2_minimum")
    if float(diversity_stats["tier_4_pct"]) > 15.0:
        violations.append("tier_4_maximum")
    return violations


def _diversity_notes(*, violations: Iterable[str], target_size: int, actual_size: int) -> list[str]:
    notes: list[str] = []
    violation_set = set(violations)
    if actual_size < target_size:
        notes.append(
            f"Evidence pack selected {actual_size} item(s) out of requested {target_size} after diversity filtering."
        )
    if "publisher_dominance" in violation_set:
        notes.append(
            "Publisher dominance cap could not be satisfied with the available evidence pool."
        )
    if "tier_1_2_minimum" in violation_set:
        notes.append(
            "Tier 1/2 minimum share could not be satisfied with the available evidence pool."
        )
    if "tier_4_maximum" in violation_set:
        notes.append(
            "Tier 4 maximum share could not be satisfied with the available evidence pool."
        )
    return notes


def _diversity_level(*, violations: Iterable[str], items: list[dict[str, Any]]) -> str:
    violation_list = list(violations)
    if not items:
        return "fail"
    if len(violation_list) >= 1:
        return "fail"
    return "pass"


def _published_timestamp(row: Mapping[str, Any]) -> float:
    published_at = row.get("published_at")
    if not published_at:
        return 0.0
    try:
        return (
            datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .timestamp()
        )
    except ValueError as exc:
        raise ValueError(f"Invalid evidence-pack row published_at value: {published_at}") from exc


def _recency_score(
    *,
    published_timestamp: float,
    oldest_timestamp: float,
    newest_timestamp: float,
) -> float:
    if newest_timestamp <= oldest_timestamp:
        return 1.0
    return round(
        (published_timestamp - oldest_timestamp) / (newest_timestamp - oldest_timestamp), 6
    )


def _credibility_score(credibility_tier: int) -> float:
    scores = {
        1: 1.0,
        2: 0.8,
        3: 0.6,
        4: 0.3,
    }
    if credibility_tier not in scores:
        raise ValueError(f"Invalid evidence-pack credibility tier: {credibility_tier}")
    return scores[credibility_tier]


def _validate_row(row: Mapping[str, Any]) -> None:
    required_fields = ("chunk_id", "text", "source_id", "publisher", "credibility_tier")
    missing_fields = [field for field in required_fields if row.get(field) in (None, "")]
    if missing_fields:
        raise ValueError(f"Invalid evidence-pack row: missing {', '.join(missing_fields)}")


def _normalized_optional_score(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    score = float(value)
    return min(1.0, max(0.0, score))


def _load_top_semantic_rows(
    *,
    connection: sqlite3.Connection,
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    cursor = connection.execute(
        f"""
        SELECT
          chunk_id,
          doc_id,
          publisher,
          source_id,
          published_at,
          credibility_tier,
          semantic_score,
          text
        FROM {FTS_TABLE_NAME}
        WHERE COALESCE(semantic_score, 0.0) > 0.0
        ORDER BY COALESCE(semantic_score, 0.0) DESC, chunk_id ASC
        LIMIT ?
        """,
        (limit,),
    )
    columns = [column[0] for column in cursor.description or []]
    rows = [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
    return [
        {
            "chunk_id": row["chunk_id"],
            "doc_id": row["doc_id"],
            "publisher": row["publisher"],
            "source_id": row["source_id"],
            "published_at": row["published_at"],
            "credibility_tier": int(row["credibility_tier"]),
            "semantic_score": _normalized_optional_score(row["semantic_score"]),
            "lexical_score": 0.0,
            "text": row["text"],
        }
        for row in rows
    ]


def _merge_hybrid_candidate_rows(
    *,
    lexical_rows: Iterable[Mapping[str, Any]],
    semantic_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in lexical_rows:
        chunk_id = str(row["chunk_id"])
        merged[chunk_id] = dict(row)
    for row in semantic_rows:
        chunk_id = str(row["chunk_id"])
        if chunk_id not in merged:
            merged[chunk_id] = dict(row)
            continue
        merged[chunk_id]["semantic_score"] = _normalized_optional_score(
            row.get("semantic_score", merged[chunk_id].get("semantic_score"))
        )
    return list(merged.values())
