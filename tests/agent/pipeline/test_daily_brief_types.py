from __future__ import annotations

import unittest
from typing import get_args

from apps.agent.pipeline.types import (
    DailyBriefClaimKind,
    DailyBriefIssue,
    DailyBriefNoveltyLabel,
    DailyBriefSynthesisV2,
    IssueMap,
    StructuredClaim,
)


class DailyBriefTypeContractsTests(unittest.TestCase):
    def test_issue_map_contract_exposes_required_fields(self) -> None:
        self.assertEqual(
            set(IssueMap.__annotations__),
            {
                "issue_id",
                "issue_question",
                "thesis_hint",
                "supporting_evidence_ids",
                "opposing_evidence_ids",
                "minority_evidence_ids",
                "watch_evidence_ids",
            },
        )

    def test_structured_claim_contract_exposes_required_fields(self) -> None:
        self.assertEqual(
            set(StructuredClaim.__annotations__),
            {
                "claim_id",
                "issue_id",
                "claim_kind",
                "claim_text",
                "supporting_citation_ids",
                "opposing_citation_ids",
                "confidence",
                "novelty_vs_prior_brief",
                "why_it_matters",
            },
        )

    def test_issue_centered_synthesis_groups_claims_by_issue(self) -> None:
        self.assertEqual(
            set(DailyBriefIssue.__annotations__),
            {
                "issue_id",
                "issue_question",
                "title",
                "summary",
                "prevailing",
                "counter",
                "minority",
                "watch",
                "coverage_summary",
            },
        )
        self.assertEqual(
            set(DailyBriefSynthesisV2.__annotations__),
            {"brief", "issues", "claim_deltas", "meta", "changed"},
        )

    def test_literal_vocabularies_match_redesign(self) -> None:
        self.assertEqual(
            set(get_args(DailyBriefClaimKind)),
            {"prevailing", "counter", "minority", "watch"},
        )
        self.assertEqual(
            set(get_args(DailyBriefNoveltyLabel)),
            {"new", "continued", "reframed", "weakened", "strengthened", "reversed", "unknown"},
        )


if __name__ == "__main__":
    unittest.main()
