from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from apps.agent.pipeline.types import (
    BriefPlan,
    IssueInformationGain,
    IssueMap,
    IssueOverlapReport,
)

HIGH_OVERLAP_THRESHOLD = 0.65
MIN_INFORMATION_GAIN_SCORE = 0.55


def dedupe_issues(
    *,
    issue_map: Iterable[IssueMap],
    brief_plan: BriefPlan,
) -> tuple[list[IssueMap], list[IssueOverlapReport], list[IssueInformationGain]]:
    ordered_issues = [dict(issue) for issue in issue_map]
    kept: list[IssueMap] = []
    overlap_reports: list[IssueOverlapReport] = []
    information_gain_reports: list[IssueInformationGain] = []

    for issue in ordered_issues:
        if len(kept) >= int(brief_plan["issue_budget"]):
            information_gain_reports.append(
                IssueInformationGain(
                    issue_id=str(issue["issue_id"]),
                    information_gain_score=0.0,
                    decision="drop",
                    reason_codes=["issue_budget_exceeded"],
                )
            )
            continue
        duplicate_target: IssueMap | None = None
        max_overlap_score = 0.0
        for kept_issue in kept:
            report = _overlap_report(left_issue=kept_issue, right_issue=issue)
            overlap_reports.append(report)
            report_score = max(
                float(report["question_token_overlap"]),
                float(report["citation_overlap"]),
                float(report["source_overlap"]),
            )
            max_overlap_score = max(max_overlap_score, report_score)
            if report["decision"] == "merge":
                duplicate_target = kept_issue
                break
        if duplicate_target is not None:
            _merge_into(target=duplicate_target, issue=issue)
            information_gain_reports.append(
                IssueInformationGain(
                    issue_id=str(issue["issue_id"]),
                    information_gain_score=round(1.0 - max_overlap_score, 2),
                    decision="drop",
                    reason_codes=["restates_existing_issue", "low_incremental_value"],
                )
            )
            continue

        info_gain_score = round(1.0 - max_overlap_score, 2)
        decision = "keep"
        reason_codes = ["distinct_issue"]
        if kept and info_gain_score < MIN_INFORMATION_GAIN_SCORE:
            decision = "drop"
            reason_codes = ["low_incremental_value", "restates_existing_issue"]
        information_gain_reports.append(
            IssueInformationGain(
                issue_id=str(issue["issue_id"]),
                information_gain_score=info_gain_score,
                decision=decision,
                reason_codes=reason_codes,
            )
        )
        if decision == "keep":
            kept.append(issue)

    return kept, overlap_reports, information_gain_reports


def _overlap_report(*, left_issue: Mapping[str, Any], right_issue: Mapping[str, Any]) -> IssueOverlapReport:
    question_overlap = _jaccard(
        _tokens(str(left_issue.get("issue_question") or "")),
        _tokens(str(right_issue.get("issue_question") or "")),
    )
    citation_overlap = _evidence_overlap(left_issue=left_issue, right_issue=right_issue)
    source_overlap = _source_overlap(left_issue=left_issue, right_issue=right_issue)
    thesis_overlap_score = _jaccard(
        _tokens(str(left_issue.get("thesis_hint") or "")),
        _tokens(str(right_issue.get("thesis_hint") or "")),
    )
    decision = "keep"
    reason_codes: list[str] = []
    if max(question_overlap, citation_overlap, source_overlap, thesis_overlap_score) >= HIGH_OVERLAP_THRESHOLD:
        decision = "merge"
        if citation_overlap >= HIGH_OVERLAP_THRESHOLD:
            reason_codes.append("high_citation_overlap")
        if question_overlap >= HIGH_OVERLAP_THRESHOLD or thesis_overlap_score >= HIGH_OVERLAP_THRESHOLD:
            reason_codes.append("same_underlying_thesis")

    thesis_overlap = "low"
    if thesis_overlap_score >= HIGH_OVERLAP_THRESHOLD:
        thesis_overlap = "high"
    elif thesis_overlap_score >= 0.35:
        thesis_overlap = "medium"

    return IssueOverlapReport(
        left_issue_id=str(left_issue["issue_id"]),
        right_issue_id=str(right_issue["issue_id"]),
        question_token_overlap=round(question_overlap, 2),
        citation_overlap=round(citation_overlap, 2),
        source_overlap=round(source_overlap, 2),
        thesis_overlap=thesis_overlap,
        decision=decision,
        reason_codes=reason_codes,
    )


def _merge_into(*, target: IssueMap, issue: Mapping[str, Any]) -> None:
    for field in (
        "supporting_evidence_ids",
        "opposing_evidence_ids",
        "minority_evidence_ids",
        "watch_evidence_ids",
    ):
        merged: list[str] = []
        for value in list(target.get(field, [])) + list(issue.get(field, [])):
            if value not in merged:
                merged.append(str(value))
        target[field] = merged


def _evidence_overlap(*, left_issue: Mapping[str, Any], right_issue: Mapping[str, Any]) -> float:
    left_ids = _issue_evidence_ids(left_issue)
    right_ids = _issue_evidence_ids(right_issue)
    return _jaccard(left_ids, right_ids)


def _source_overlap(*, left_issue: Mapping[str, Any], right_issue: Mapping[str, Any]) -> float:
    left_prefixes = {chunk_id.rsplit("_chunk_", 1)[0] for chunk_id in _issue_evidence_ids(left_issue)}
    right_prefixes = {chunk_id.rsplit("_chunk_", 1)[0] for chunk_id in _issue_evidence_ids(right_issue)}
    return _jaccard(left_prefixes, right_prefixes)


def _issue_evidence_ids(issue: Mapping[str, Any]) -> set[str]:
    evidence_ids: set[str] = set()
    for field in (
        "supporting_evidence_ids",
        "opposing_evidence_ids",
        "minority_evidence_ids",
        "watch_evidence_ids",
    ):
        values = issue.get(field, [])
        if not isinstance(values, list):
            continue
        evidence_ids.update(str(value) for value in values if isinstance(value, str))
    return evidence_ids


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)
