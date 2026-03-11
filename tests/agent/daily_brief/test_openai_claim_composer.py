from __future__ import annotations

import unittest

from apps.agent.daily_brief.model_interfaces import ClaimComposerInput
from apps.agent.daily_brief.openai_claim_composer import OpenAIClaimComposer


class OpenAIClaimComposerTests(unittest.TestCase):
    def test_composes_claims_from_schema_valid_json(self) -> None:
        composer = OpenAIClaimComposer(
            response_loader=lambda _brief_input: """
            [
              {
                "claim_id": "claim_oil_prevailing",
                "issue_id": "issue_oil",
                "claim_kind": "prevailing",
                "claim_text": "Most sources still expect near-term upside in oil prices.",
                "supporting_citation_ids": ["cite_001", "cite_002"],
                "opposing_citation_ids": ["cite_003"],
                "confidence": "medium",
                "novelty_vs_prior_brief": "strengthened",
                "why_it_matters": "Near-term energy inflation risk remains elevated."
              }
            ]
            """
        )

        result = composer.compose_claims(
            brief_input=ClaimComposerInput(
                run_id="run_001",
                generated_at_utc="2026-03-12T00:00:00Z",
                issue_map=[
                    {
                        "issue_id": "issue_oil",
                        "issue_question": "Will oil prices keep rising over the next few weeks?",
                        "thesis_hint": "Supply concerns are keeping near-term pressure skewed upward.",
                        "supporting_evidence_ids": ["chunk_1"],
                        "opposing_evidence_ids": ["chunk_2"],
                        "minority_evidence_ids": ["chunk_3"],
                        "watch_evidence_ids": ["chunk_4"],
                    }
                ],
                citation_store={"cite_001": {"citation_id": "cite_001"}},
                prior_brief_context=None,
            )
        )

        self.assertEqual(result[0]["claim_kind"], "prevailing")
        self.assertEqual(result[0]["novelty_vs_prior_brief"], "strengthened")

    def test_rejects_malformed_claim_output(self) -> None:
        composer = OpenAIClaimComposer(response_loader=lambda _brief_input: '[{"claim_id": "missing_fields"}]')

        with self.assertRaises(ValueError):
            composer.compose_claims(
                brief_input=ClaimComposerInput(
                    run_id="run_001",
                    generated_at_utc="2026-03-12T00:00:00Z",
                    issue_map=[],
                    citation_store={},
                    prior_brief_context=None,
                )
            )

    def test_rejects_wrong_claim_field_types_and_enum_values(self) -> None:
        composer = OpenAIClaimComposer(
            response_loader=lambda _brief_input: """
            [
              {
                "claim_id": "claim_oil_prevailing",
                "issue_id": "issue_oil",
                "claim_kind": "dominant",
                "claim_text": "Most sources still expect near-term upside in oil prices.",
                "supporting_citation_ids": "cite_001",
                "opposing_citation_ids": ["cite_003"],
                "confidence": "medium",
                "novelty_vs_prior_brief": "stronger",
                "why_it_matters": "Near-term energy inflation risk remains elevated."
              }
            ]
            """
        )

        with self.assertRaises(ValueError):
            composer.compose_claims(
                brief_input=ClaimComposerInput(
                    run_id="run_001",
                    generated_at_utc="2026-03-12T00:00:00Z",
                    issue_map=[],
                    citation_store={},
                    prior_brief_context=None,
                )
            )


if __name__ == "__main__":
    unittest.main()
