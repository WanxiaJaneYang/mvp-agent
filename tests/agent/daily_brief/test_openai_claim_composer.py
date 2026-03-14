from __future__ import annotations

import unittest

from apps.agent.daily_brief.model_interfaces import ClaimComposerInput
from apps.agent.daily_brief.openai_claim_composer import OpenAIClaimComposer


class OpenAIClaimComposerTests(unittest.TestCase):
    def test_build_request_payload_preserves_issue_map_citation_store_and_prior_context(self) -> None:
        composer = OpenAIClaimComposer(response_loader=lambda _brief_input: [])
        brief_input = ClaimComposerInput(
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
            prior_brief_context={"issue_count": 1, "claim_summaries": ["Yesterday's prevailing claim."]},
        )

        payload = composer.build_request_payload(brief_input=brief_input)

        self.assertEqual(payload["run_id"], "run_001")
        self.assertEqual(payload["input"]["issue_map"][0]["issue_id"], "issue_oil")
        self.assertEqual(payload["input"]["citation_store"]["cite_001"]["citation_id"], "cite_001")
        self.assertEqual(payload["input"]["prior_brief_context"]["issue_count"], 1)
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertEqual(payload["messages"][0]["role"], "system")

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
                citation_store={
                    "cite_001": {"citation_id": "cite_001", "chunk_id": "chunk_1"},
                    "cite_002": {"citation_id": "cite_002", "chunk_id": "chunk_1"},
                    "cite_003": {"citation_id": "cite_003", "chunk_id": "chunk_2"},
                },
                prior_brief_context=None,
            )
        )

        self.assertEqual(result[0]["claim_kind"], "prevailing")
        self.assertEqual(result[0]["novelty_vs_prior_brief"], "strengthened")

    def test_composes_claims_using_explicit_request_payload_boundary(self) -> None:
        captured_payload = {}

        def _loader(brief_input):
            captured_payload.update(brief_input)
            return [
                {
                    "claim_id": "claim_oil_prevailing",
                    "issue_id": "issue_oil",
                    "claim_kind": "prevailing",
                    "claim_text": "Most sources still expect near-term upside in oil prices.",
                    "supporting_citation_ids": ["cite_001", "cite_002"],
                    "opposing_citation_ids": ["cite_003"],
                    "confidence": "medium",
                    "novelty_vs_prior_brief": "strengthened",
                    "why_it_matters": "Near-term energy inflation risk remains elevated.",
                }
            ]

        composer = OpenAIClaimComposer(response_loader=_loader)
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
                citation_store={
                    "cite_001": {"citation_id": "cite_001", "chunk_id": "chunk_1"},
                    "cite_002": {"citation_id": "cite_002", "chunk_id": "chunk_1"},
                    "cite_003": {"citation_id": "cite_003", "chunk_id": "chunk_2"},
                },
                prior_brief_context={"issue_count": 1},
            )
        )

        self.assertEqual(captured_payload["run_id"], "run_001")
        self.assertEqual(captured_payload["input"]["prior_brief_context"]["issue_count"], 1)
        self.assertEqual(result[0]["claim_id"], "claim_oil_prevailing")

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

    def test_rejects_claims_without_supporting_citation_ids(self) -> None:
        composer = OpenAIClaimComposer(
            response_loader=lambda _brief_input: """
            [
              {
                "claim_id": "claim_oil_prevailing",
                "issue_id": "issue_oil",
                "claim_kind": "prevailing",
                "claim_text": "Most sources still expect near-term upside in oil prices.",
                "supporting_citation_ids": [],
                "opposing_citation_ids": ["cite_003"],
                "confidence": "medium",
                "novelty_vs_prior_brief": "unknown",
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

    def test_rejects_claims_that_borrow_citations_from_another_issue(self) -> None:
        composer = OpenAIClaimComposer(
            response_loader=lambda _brief_input: """
            [
              {
                "claim_id": "claim_oil_prevailing",
                "issue_id": "issue_oil",
                "claim_kind": "prevailing",
                "claim_text": "Most sources still expect near-term upside in oil prices.",
                "supporting_citation_ids": ["cite_002"],
                "opposing_citation_ids": [],
                "confidence": "medium",
                "novelty_vs_prior_brief": "continued",
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
                    issue_map=[
                        {
                            "issue_id": "issue_oil",
                            "issue_question": "Will oil prices keep rising over the next few weeks?",
                            "thesis_hint": "Supply concerns are keeping near-term pressure skewed upward.",
                            "supporting_evidence_ids": ["chunk_1"],
                            "opposing_evidence_ids": ["chunk_2"],
                            "minority_evidence_ids": ["chunk_3"],
                            "watch_evidence_ids": ["chunk_4"],
                        },
                        {
                            "issue_id": "issue_refining",
                            "issue_question": "Will refining bottlenecks keep product spreads wide?",
                            "thesis_hint": "Outages are keeping downstream stress elevated.",
                            "supporting_evidence_ids": ["chunk_5"],
                            "opposing_evidence_ids": ["chunk_6"],
                            "minority_evidence_ids": [],
                            "watch_evidence_ids": ["chunk_7"],
                        },
                    ],
                    citation_store={
                        "cite_001": {"citation_id": "cite_001", "chunk_id": "chunk_1"},
                        "cite_002": {"citation_id": "cite_002", "chunk_id": "chunk_5"},
                    },
                    prior_brief_context=None,
                )
            )

    def test_rejects_claims_when_supporting_citations_break_bucket_semantics(self) -> None:
        composer = OpenAIClaimComposer(
            response_loader=lambda _brief_input: """
            [
              {
                "claim_id": "claim_oil_prevailing",
                "issue_id": "issue_oil",
                "claim_kind": "prevailing",
                "claim_text": "Most sources still expect near-term upside in oil prices.",
                "supporting_citation_ids": ["cite_watch"],
                "opposing_citation_ids": [],
                "confidence": "medium",
                "novelty_vs_prior_brief": "continued",
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
                    citation_store={
                        "cite_support": {"citation_id": "cite_support", "chunk_id": "chunk_1"},
                        "cite_watch": {"citation_id": "cite_watch", "chunk_id": "chunk_4"},
                    },
                    prior_brief_context=None,
                )
            )

    def test_rejects_claims_when_opposing_citations_break_bucket_semantics(self) -> None:
        composer = OpenAIClaimComposer(
            response_loader=lambda _brief_input: """
            [
              {
                "claim_id": "claim_oil_prevailing",
                "issue_id": "issue_oil",
                "claim_kind": "prevailing",
                "claim_text": "Most sources still expect near-term upside in oil prices.",
                "supporting_citation_ids": ["cite_support"],
                "opposing_citation_ids": ["cite_watch"],
                "confidence": "medium",
                "novelty_vs_prior_brief": "continued",
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
                    citation_store={
                        "cite_support": {"citation_id": "cite_support", "chunk_id": "chunk_1"},
                        "cite_counter": {"citation_id": "cite_counter", "chunk_id": "chunk_2"},
                        "cite_watch": {"citation_id": "cite_watch", "chunk_id": "chunk_4"},
                    },
                    prior_brief_context=None,
                )
            )


if __name__ == "__main__":
    unittest.main()
