from __future__ import annotations

import unittest

from apps.agent.daily_brief.delta import build_changed_section_from_deltas, build_claim_deltas


class DailyBriefDeltaTests(unittest.TestCase):
    def test_build_claim_deltas_preserves_novelty_label_and_prior_match(self) -> None:
        deltas = build_claim_deltas(
            structured_claims=[
                {
                    "claim_id": "claim_001",
                    "issue_id": "issue_001",
                    "claim_kind": "prevailing",
                    "claim_text": "Softer growth is strengthening later-cut expectations.",
                    "supporting_citation_ids": ["cite_001"],
                    "opposing_citation_ids": [],
                    "confidence": "medium",
                    "novelty_vs_prior_brief": "strengthened",
                    "why_it_matters": "Rate-sensitive assets can reprice quickly.",
                }
            ],
            prior_brief_context={
                "claim_texts": [
                    "Softer growth was already nudging later-cut expectations."
                ]
            },
        )

        self.assertEqual(deltas[0]["novelty_label"], "strengthened")
        self.assertIsNotNone(deltas[0]["prior_claim_ref"])
        self.assertEqual(deltas[0]["supporting_prior_overlap"]["thesis_overlap"], "medium")

    def test_build_changed_section_from_deltas_renders_only_changed_labels(self) -> None:
        changed = build_changed_section_from_deltas(
            structured_claims=[
                {
                    "claim_id": "claim_001",
                    "issue_id": "issue_001",
                    "claim_kind": "prevailing",
                    "claim_text": "Softer growth is strengthening later-cut expectations.",
                    "supporting_citation_ids": ["cite_001"],
                    "opposing_citation_ids": [],
                    "confidence": "medium",
                    "novelty_vs_prior_brief": "strengthened",
                    "why_it_matters": "Rate-sensitive assets can reprice quickly.",
                },
                {
                    "claim_id": "claim_002",
                    "issue_id": "issue_001",
                    "claim_kind": "counter",
                    "claim_text": "Policy language remains cautious.",
                    "supporting_citation_ids": ["cite_002"],
                    "opposing_citation_ids": [],
                    "confidence": "medium",
                    "novelty_vs_prior_brief": "continued",
                    "why_it_matters": "Cuts are not imminent.",
                },
            ],
            claim_deltas=[
                {
                    "claim_id": "claim_001",
                    "prior_claim_ref": "prior claim",
                    "novelty_label": "strengthened",
                    "delta_explanation": "New official release reinforced the thesis.",
                    "supporting_prior_overlap": {
                        "citation_overlap": 0.5,
                        "thesis_overlap": "medium",
                    },
                },
                {
                    "claim_id": "claim_002",
                    "prior_claim_ref": "prior claim",
                    "novelty_label": "continued",
                    "delta_explanation": "No real change.",
                    "supporting_prior_overlap": {
                        "citation_overlap": 0.8,
                        "thesis_overlap": "high",
                    },
                },
            ],
        )

        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0]["delta_label"], "strengthened")
        self.assertIn("New official release", changed[0]["delta_explanation"])


if __name__ == "__main__":
    unittest.main()
