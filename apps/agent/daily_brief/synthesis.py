from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from apps.agent.pipeline.types import (
    DAILY_BRIEF_CORE_OUTPUT_SECTIONS,
    BriefPlan,
    CitationStoreEntry,
    ClaimEvidenceItem,
    DailyBriefBullet,
    DailyBriefIssue,
    DailyBriefOutputSection,
    DailyBriefSynthesis,
    DailyBriefSynthesisV2,
    EvidencePackItem,
    IssueMap,
    RuntimeChunkRow,
    RuntimeDocumentRecord,
    StructuredClaim,
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
WATCH_STRICT_KEYWORDS = (
    "ahead",
    "monitor",
    "next",
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
INSUFFICIENT_EVIDENCE_TEXT = "[Insufficient evidence to produce a validated output]"
CHANGED_SECTION_MAX_BULLETS = 3
SECTION_BULLET_LIMITS: dict[DailyBriefOutputSection, int] = {
    "prevailing": 3,
    "counter": 2,
    "minority": 2,
    "watch": 3,
    "changed": CHANGED_SECTION_MAX_BULLETS,
}
SECTION_STRICT_SCORE_FLOORS: dict[DailyBriefOutputSection, int] = {
    "prevailing": 0,
    "counter": 100,
    "minority": 100,
    "watch": 100,
    "changed": 0,
}


@dataclass(frozen=True)
class _SectionCandidate:
    chunk_id: str
    item: Mapping[str, Any]
    document: Mapping[str, Any]
    citation: Mapping[str, Any]
    citation_id: str
    scores: dict[DailyBriefOutputSection, int]


@dataclass(frozen=True)
class SynthesisRetryPlan:
    pinned_chunk_ids_by_section: Mapping[DailyBriefOutputSection, str]
    target_sections: tuple[DailyBriefOutputSection, ...]
    blocked_chunk_ids: frozenset[str]


def build_citation_store(
    *,
    evidence_items: Iterable[EvidencePackItem],
    documents_by_id: Mapping[str, RuntimeDocumentRecord],
    chunks_by_id: Mapping[str, RuntimeChunkRow],
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
    evidence_items: Iterable[EvidencePackItem],
    documents_by_id: Mapping[str, RuntimeDocumentRecord],
    citation_store: Mapping[str, CitationStoreEntry],
    retry_plan: SynthesisRetryPlan | None = None,
) -> DailyBriefSynthesis:
    synthesis: DailyBriefSynthesis = {}
    for section in DAILY_BRIEF_CORE_OUTPUT_SECTIONS:
        synthesis[section] = []
    candidates = _build_section_candidates(
        evidence_items=evidence_items,
        documents_by_id=documents_by_id,
        citation_store=citation_store,
    )
    assignments = _assign_sections(candidates, retry_plan=retry_plan)

    for section in DAILY_BRIEF_CORE_OUTPUT_SECTIONS:
        section_candidates = assignments.get(section, [])
        if not section_candidates:
            continue
        for candidate in section_candidates:
            bullet: DailyBriefBullet = {
                "text": _build_bullet_text(
                    section=section,
                    document=candidate.document,
                    citation=candidate.citation,
                    publisher=str(candidate.item["publisher"]),
                    strict_match=_is_strict_section_match(candidate=candidate, section=section),
                ),
                "citation_ids": [candidate.citation_id],
                "confidence_label": _confidence_label(int(candidate.item["credibility_tier"])),
            }
            synthesis[section].append(bullet)
    return synthesis


def build_changed_section(
    *,
    current_synthesis: Mapping[str, Any],
    previous_synthesis: Mapping[str, Any] | None,
) -> list[DailyBriefBullet]:
    if not isinstance(previous_synthesis, Mapping):
        return []

    changed: list[DailyBriefBullet] = []
    for section in DAILY_BRIEF_CORE_OUTPUT_SECTIONS:
        current_bullet = _first_synthesis_bullet(current_synthesis, section)
        if current_bullet is None:
            continue

        current_text = str(current_bullet.get("text", "")).strip()
        if not current_text or current_text == INSUFFICIENT_EVIDENCE_TEXT:
            continue

        previous_bullet = _first_synthesis_bullet(previous_synthesis, section)
        previous_text = "" if previous_bullet is None else str(previous_bullet.get("text", "")).strip()
        if current_text == previous_text:
            continue

        changed_bullet: DailyBriefBullet = {
            "text": _build_changed_bullet_text(
                section=section,
                current_text=current_text,
                previous_text=previous_text,
            ),
            "citation_ids": [
                str(citation_id) for citation_id in current_bullet.get("citation_ids", [])
            ],
        }
        confidence_label = current_bullet.get("confidence_label")
        if isinstance(confidence_label, str):
            changed_bullet["confidence_label"] = confidence_label
        changed.append(changed_bullet)
        if len(changed) >= CHANGED_SECTION_MAX_BULLETS:
            break

    return changed


def build_synthesis_from_structured_claims(
    *,
    brief_plan: BriefPlan | None = None,
    issue_map: Iterable[IssueMap],
    structured_claims: Iterable[StructuredClaim],
    citation_store: Mapping[str, CitationStoreEntry],
) -> DailyBriefSynthesisV2:
    claims_by_issue_id: dict[str, list[StructuredClaim]] = {}
    for claim in structured_claims:
        claims_by_issue_id.setdefault(str(claim["issue_id"]), []).append(claim)

    issues: list[DailyBriefIssue] = []
    for issue in issue_map:
        issue_id = str(issue["issue_id"])
        issue_claims = claims_by_issue_id.get(issue_id, [])
        issues.append(
            DailyBriefIssue(
                issue_id=issue_id,
                issue_question=str(issue["issue_question"]),
                title=str(issue["issue_question"]),
                summary=str(issue.get("thesis_hint") or issue["issue_question"]),
                prevailing=_bullets_for_issue(issue_claims, "prevailing", citation_store),
                counter=_bullets_for_issue(issue_claims, "counter", citation_store),
                minority=_bullets_for_issue(issue_claims, "minority", citation_store),
                watch=_bullets_for_issue(issue_claims, "watch", citation_store),
            )
        )

    synthesis = DailyBriefSynthesisV2(
        issues=issues,
        meta={"status": "validated"},
    )
    if brief_plan is not None:
        synthesis["brief"] = {
            "bottom_line": brief_plan["brief_thesis"],
            "top_takeaways": list(brief_plan["top_takeaways"]),
            "watchlist": list(brief_plan["watchlist"]),
            "render_mode": brief_plan["render_mode"],
            "source_scarcity_mode": brief_plan["source_scarcity_mode"],
            "issue_budget": brief_plan["issue_budget"],
        }
    return synthesis


def _bullets_for_issue(
    issue_claims: Iterable[StructuredClaim],
    claim_kind: str,
    citation_store: Mapping[str, CitationStoreEntry],
) -> list[DailyBriefBullet]:
    bullets: list[DailyBriefBullet] = []
    for claim in issue_claims:
        if claim["claim_kind"] != claim_kind:
            continue
        supporting_citation_ids = list(claim["supporting_citation_ids"])
        bullet: DailyBriefBullet = {
            "text": str(claim["claim_text"]),
            "citation_ids": supporting_citation_ids,
            "confidence_label": str(claim["confidence"]),
        }
        evidence = _build_evidence_items(
            citation_ids=supporting_citation_ids,
            citation_store=citation_store,
        )
        if evidence:
            bullet["evidence"] = evidence
        bullets.append(bullet)
    return bullets


def _build_evidence_items(
    *,
    citation_ids: Iterable[str],
    citation_store: Mapping[str, CitationStoreEntry],
) -> list[ClaimEvidenceItem]:
    evidence: list[ClaimEvidenceItem] = []
    for citation_id in citation_ids:
        citation = citation_store.get(str(citation_id))
        if citation is None:
            continue
        evidence.append(
            ClaimEvidenceItem(
                citation_id=str(citation_id),
                publisher=str(citation.get("publisher") or ""),
                published_at=citation.get("published_at"),
                support_text=str(
                    citation.get("snippet_text")
                    or citation.get("quote_text")
                    or citation.get("title")
                    or ""
                ),
            )
        )
    return evidence


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
    evidence_items: Iterable[EvidencePackItem],
    documents_by_id: Mapping[str, RuntimeDocumentRecord],
    citation_store: Mapping[str, CitationStoreEntry],
) -> list[_SectionCandidate]:
    citations_by_chunk_id = {
        str(entry["chunk_id"]): (str(citation_id), entry)
        for citation_id, entry in citation_store.items()
        if isinstance(entry, Mapping) and entry.get("chunk_id") is not None
    }
    candidates: list[_SectionCandidate] = []
    for item in _sorted_evidence_items(evidence_items):
        chunk_id = str(item["chunk_id"])
        citation_payload = citations_by_chunk_id.get(chunk_id)
        if citation_payload is None:
            continue
        citation_id, citation = citation_payload
        document = documents_by_id[str(item["doc_id"])]
        candidates.append(
            _SectionCandidate(
                chunk_id=chunk_id,
                item=item,
                document=document,
                citation=citation,
                citation_id=citation_id,
                scores=_section_scores(item=item, document=document),
            )
        )
    return candidates


def _assign_sections(
    candidates: Iterable[_SectionCandidate],
    *,
    retry_plan: SynthesisRetryPlan | None = None,
) -> dict[DailyBriefOutputSection, list[_SectionCandidate]]:
    ordered_candidates = list(candidates)
    candidates_by_chunk_id = {candidate.chunk_id: candidate for candidate in ordered_candidates}
    blocked_chunk_ids: frozenset[str] = frozenset()
    assignments: dict[DailyBriefOutputSection, list[_SectionCandidate]] = {}
    used_chunk_ids: set[str] = set()
    search_order: tuple[DailyBriefOutputSection, ...] = ("watch", "counter", "minority", "prevailing")

    if retry_plan is not None:
        blocked_chunk_ids = frozenset(retry_plan.blocked_chunk_ids)
        for section, chunk_id in retry_plan.pinned_chunk_ids_by_section.items():
            candidate = candidates_by_chunk_id.get(chunk_id)
            if candidate is None or candidate.chunk_id in blocked_chunk_ids:
                continue
            assignments.setdefault(section, []).append(candidate)
            used_chunk_ids.add(candidate.chunk_id)
        prioritized_targets = tuple(
            section
            for section in retry_plan.target_sections
            if section not in assignments
        )
        remaining_sections = tuple(
            section
            for section in search_order
            if section not in assignments and section not in prioritized_targets
        )
        search_order = prioritized_targets + remaining_sections

    initial_assignment = _best_single_assignment(
        ordered_candidates=ordered_candidates,
        search_order=search_order,
        seeded_assignment={section: items[0] for section, items in assignments.items()},
        blocked_chunk_ids=blocked_chunk_ids,
    )
    assignments = {section: [candidate] for section, candidate in initial_assignment.items()}
    used_chunk_ids = {candidate.chunk_id for candidate in initial_assignment.values()}

    if retry_plan is not None:
        return assignments

    for section in search_order:
        section_candidates = assignments.setdefault(section, [])
        if section_candidates and not _has_validation_safe_lead(section_candidates[0]):
            continue
        section_limit = SECTION_BULLET_LIMITS[section]
        if retry_plan is not None:
            if section in retry_plan.pinned_chunk_ids_by_section:
                section_limit = len(section_candidates)
            elif section in retry_plan.target_sections:
                section_limit = 1
        ranked_candidates = sorted(
            ordered_candidates,
            key=lambda candidate: _section_sort_key(section=section, candidate=candidate),
            reverse=True,
        )
        for candidate in ranked_candidates:
            if len(section_candidates) >= section_limit:
                break
            if candidate.chunk_id in used_chunk_ids or candidate.chunk_id in blocked_chunk_ids:
                continue
            if section != "prevailing" and not _is_strict_section_match(candidate=candidate, section=section):
                continue
            section_candidates.append(candidate)
            used_chunk_ids.add(candidate.chunk_id)
        if section != "prevailing" and not section_candidates:
            for candidate in ranked_candidates:
                if candidate.chunk_id in used_chunk_ids or candidate.chunk_id in blocked_chunk_ids:
                    continue
                section_candidates.append(candidate)
                used_chunk_ids.add(candidate.chunk_id)
                break

    return {section: items for section, items in assignments.items() if items}


def _best_single_assignment(
    *,
    ordered_candidates: list[_SectionCandidate],
    search_order: tuple[DailyBriefOutputSection, ...],
    seeded_assignment: Mapping[DailyBriefOutputSection, _SectionCandidate],
    blocked_chunk_ids: frozenset[str],
) -> dict[DailyBriefOutputSection, _SectionCandidate]:
    best_assignment: dict[DailyBriefOutputSection, _SectionCandidate] = {}
    best_key: tuple[int, tuple[tuple[int, int, str], ...]] | None = None
    seeded_chunk_ids = frozenset(candidate.chunk_id for candidate in seeded_assignment.values())

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
        if section in seeded_assignment:
            search(section_index + 1, used_chunk_ids, assignment)
            return

        assigned_any = False
        for candidate in ordered_candidates:
            if candidate.chunk_id in used_chunk_ids or candidate.chunk_id in blocked_chunk_ids:
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

    search(0, seeded_chunk_ids, dict(seeded_assignment))
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

def _is_strict_section_match(
    *,
    candidate: _SectionCandidate,
    section: DailyBriefOutputSection,
) -> bool:
    if section == "prevailing":
        return True
    keyword_sets: dict[DailyBriefOutputSection, tuple[str, ...]] = {
        "counter": COUNTER_KEYWORDS,
        "minority": MINORITY_KEYWORDS,
        "watch": WATCH_STRICT_KEYWORDS,
        "prevailing": (),
        "changed": (),
    }
    text = _normalized_document_text(candidate.document)
    keywords = keyword_sets[section]
    if keywords:
        return any(keyword in text for keyword in keywords)
    return candidate.scores[section] >= SECTION_STRICT_SCORE_FLOORS[section]


def _section_sort_key(
    *,
    section: DailyBriefOutputSection,
    candidate: _SectionCandidate,
) -> tuple[int, int, int, str]:
    credibility_priority = 0
    if section == "watch":
        credibility_priority = max(0, 5 - int(candidate.item.get("credibility_tier", 4))) * 10
    return (
        credibility_priority,
        candidate.scores[section],
        -int(candidate.item.get("rank_in_pack", 9999)),
        candidate.chunk_id,
    )


def _has_validation_safe_lead(candidate: _SectionCandidate) -> bool:
    return bool(candidate.citation.get("url")) and bool(candidate.citation.get("published_at"))


def _build_bullet_text(
    *,
    section: str,
    document: Mapping[str, Any],
    citation: Mapping[str, Any],
    publisher: str,
    strict_match: bool,
) -> str:
    del publisher
    if section in {"counter", "watch"}:
        preferred_text = document.get("title")
    elif strict_match:
        preferred_text = (
            citation.get("quote_text")
            or citation.get("snippet_text")
            or document.get("rss_snippet")
        )
    else:
        preferred_text = document.get("title")
    sentence = _normalized_sentence(
        str(
            preferred_text
            or citation.get("snippet_text")
            or citation.get("quote_text")
            or document.get("title")
            or ""
        )
    )
    if section == "counter":
        return f"Counterpoint: {sentence}"
    if section == "minority":
        return f"Minority view: {sentence}"
    if section == "watch":
        lowered = sentence[:-1].strip()
        lowered = lowered[6:] if lowered.lower().startswith("watch ") else lowered
        lowered = lowered[8:] if lowered.lower().startswith("monitor ") else lowered
        lowered = _normalize_watch_phrase(lowered)
        return f"Watch: {lowered}."
    return sentence


def _normalized_sentence(value: str) -> str:
    sentence = " ".join(part for part in value.strip().split())
    if not sentence:
        return "Evidence was available but could not be summarized."
    return f"{sentence.rstrip('.')}."


def _normalize_watch_phrase(value: str) -> str:
    phrase = value.strip()
    if not phrase:
        return phrase
    first_token = phrase.split(" ", 1)[0]
    if first_token.isupper() and len(first_token) <= 5:
        return phrase
    return phrase[:1].lower() + phrase[1:]


def _first_bullet(raw_bullets: Any) -> Mapping[str, Any] | None:
    if not isinstance(raw_bullets, list) or not raw_bullets:
        return None
    bullet = raw_bullets[0]
    if not isinstance(bullet, Mapping):
        return None
    return bullet


def _first_synthesis_bullet(
    synthesis: Mapping[str, Any],
    section: DailyBriefOutputSection,
) -> Mapping[str, Any] | None:
    issue_items = synthesis.get("issues")
    if isinstance(issue_items, list) and issue_items:
        first_issue = issue_items[0]
        if isinstance(first_issue, Mapping):
            return _first_bullet(first_issue.get(section))
    return _first_bullet(synthesis.get(section))


def _build_changed_bullet_text(*, section: str, current_text: str, previous_text: str) -> str:
    label = section.replace("_", " ").title()
    if not previous_text:
        return f"{label} is newly supported today: {current_text}"
    if previous_text == INSUFFICIENT_EVIDENCE_TEXT:
        return f"{label} gained support today: {current_text}"
    return f"{label} changed versus yesterday: {current_text}"


def _confidence_label(credibility_tier: int) -> str:
    if credibility_tier <= 1:
        return "high"
    if credibility_tier == 2:
        return "medium"
    return "low"
