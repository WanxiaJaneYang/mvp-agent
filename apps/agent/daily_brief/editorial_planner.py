from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from apps.agent.daily_brief.model_interfaces import BriefPlannerInput, BriefPlannerProvider
from apps.agent.pipeline.types import (
    BriefPlan,
    DailyBriefRenderMode,
    EvidencePackItem,
    RuntimeDocumentRecord,
    SourceScarcityMode,
)

STOPWORDS = {
    "a",
    "about",
    "and",
    "are",
    "as",
    "at",
    "for",
    "from",
    "in",
    "into",
    "is",
    "latest",
    "market",
    "markets",
    "of",
    "on",
    "or",
    "over",
    "the",
    "this",
    "today",
    "what",
    "will",
    "with",
}
WATCH_TERMS = ("ahead", "monitor", "next", "risk", "watch")


class LocalBriefPlanner(BriefPlannerProvider):
    def plan_brief(self, *, brief_input: BriefPlannerInput) -> BriefPlan:
        return plan_brief_locally(
            run_id=brief_input["run_id"],
            generated_at_utc=brief_input["generated_at_utc"],
            corpus_summary=brief_input["corpus_summary"],
            source_diversity_stats=brief_input["source_diversity_stats"],
            prior_brief_context=brief_input.get("prior_brief_context"),
        )


def build_corpus_summary(
    *,
    corpus_items: Iterable[EvidencePackItem],
    documents_by_id: Mapping[str, RuntimeDocumentRecord],
    limit: int = 4,
) -> list[str]:
    summary: list[str] = []
    for item in corpus_items:
        document = documents_by_id.get(str(item["doc_id"]))
        if document is None:
            continue
        candidate = str(document.get("rss_snippet") or document.get("title") or "").strip()
        if not candidate or candidate in summary:
            continue
        summary.append(candidate)
        if len(summary) >= limit:
            break
    return summary


def plan_brief_locally(
    *,
    run_id: str,
    generated_at_utc: str,
    corpus_summary: list[str],
    source_diversity_stats: Mapping[str, Any],
    prior_brief_context: Mapping[str, Any] | None,
) -> BriefPlan:
    candidate_issue_seeds = _candidate_issue_seeds(corpus_summary=corpus_summary)
    unique_publishers = int(source_diversity_stats.get("unique_publishers", 0) or 0)
    sparse_corpus = unique_publishers < 3 or len(candidate_issue_seeds) < 2
    issue_budget = 1 if sparse_corpus else 2
    render_mode: DailyBriefRenderMode = "compressed" if sparse_corpus else "full"
    scarcity_mode: SourceScarcityMode = "scarce" if sparse_corpus else "normal"
    watchlist = _watchlist(corpus_summary=corpus_summary)

    brief_thesis = _brief_thesis(
        corpus_summary=corpus_summary,
        candidate_issue_seeds=candidate_issue_seeds,
        prior_brief_context=prior_brief_context,
    )
    reason_codes = ["source_scarcity_detected"] if sparse_corpus else ["two_distinct_debates_supported"]
    if not sparse_corpus and len(candidate_issue_seeds) > issue_budget:
        reason_codes.append("third_issue_below_information_gain_threshold")

    top_takeaways = corpus_summary[:3] or ["Insufficient distinct evidence for a full daily brief."]
    issue_order = [f"seed_{index:03d}" for index in range(1, min(len(candidate_issue_seeds), issue_budget + 1) + 1)]
    return BriefPlan(
        brief_id=f"brief_{generated_at_utc[:10]}_{run_id}",
        brief_thesis=brief_thesis,
        top_takeaways=top_takeaways,
        issue_budget=issue_budget,
        render_mode=render_mode,
        source_scarcity_mode=scarcity_mode,
        candidate_issue_seeds=candidate_issue_seeds[:3],
        issue_order=issue_order,
        watchlist=watchlist,
        reason_codes=reason_codes,
    )


def _candidate_issue_seeds(*, corpus_summary: Iterable[str]) -> list[str]:
    seeds: list[str] = []
    counts: Counter[str] = Counter()
    for summary in corpus_summary:
        counts.update(_tokens(summary))

    ranked_terms = [term for term, _count in counts.most_common() if term not in STOPWORDS and len(term) > 3]
    while ranked_terms and len(seeds) < 3:
        current = ranked_terms.pop(0)
        related = [current]
        while ranked_terms and len(related) < 3:
            candidate = ranked_terms[0]
            if candidate[:4] == current[:4]:
                ranked_terms.pop(0)
                continue
            related.append(ranked_terms.pop(0))
        seeds.append(" ".join(related))

    if not seeds:
        return ["market narrative"]
    return seeds


def _watchlist(*, corpus_summary: Iterable[str]) -> list[str]:
    watchlist: list[str] = []
    for summary in corpus_summary:
        lowered = summary.lower()
        if any(term in lowered for term in WATCH_TERMS):
            watchlist.append(summary)
    return watchlist[:3]


def _brief_thesis(
    *,
    corpus_summary: list[str],
    candidate_issue_seeds: list[str],
    prior_brief_context: Mapping[str, Any] | None,
) -> str:
    retained_summaries = _retained_summary_lines(
        corpus_summary=corpus_summary,
        limit=2 if len(candidate_issue_seeds) >= 2 else 1,
    )
    if retained_summaries:
        thesis = " ".join(retained_summaries)
    else:
        thesis = "Today's retained evidence points to a narrower, still-developing market debate."

    previous_issue_count = 0
    if isinstance(prior_brief_context, Mapping):
        previous_issue_count = int(prior_brief_context.get("issue_count", 0) or 0)
    if previous_issue_count > 0:
        return f"{thesis} Prior context suggests continuity, but today's evidence mix remains distinct."
    return thesis


def _retained_summary_lines(*, corpus_summary: Iterable[str], limit: int) -> list[str]:
    retained: list[str] = []
    for summary in corpus_summary:
        normalized = _normalize_summary_line(summary)
        if normalized is None or normalized in retained:
            continue
        retained.append(normalized)
        if len(retained) >= limit:
            break
    return retained


def _normalize_summary_line(summary: str) -> str | None:
    collapsed = " ".join(str(summary).strip().split())
    if not collapsed:
        return None

    tokens = _tokens(collapsed)
    if len(tokens) < 3:
        return None
    if len(set(tokens)) <= max(1, len(tokens) // 3):
        return None

    normalized = collapsed[0].upper() + collapsed[1:] if len(collapsed) > 1 else collapsed.upper()
    if normalized[-1] not in ".!?":
        normalized = f"{normalized}."
    return normalized


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())
