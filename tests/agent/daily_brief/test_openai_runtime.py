import json
import unittest

from apps.agent.daily_brief.model_interfaces import ClaimComposerInput, IssuePlannerInput
from apps.agent.daily_brief.openai_claim_composer import OpenAIClaimComposer
from apps.agent.daily_brief.openai_issue_planner import OpenAIIssuePlanner
from apps.agent.daily_brief.openai_runtime import OpenAIResponsesTextClient


class _FakeResponsesApi:
    def __init__(self) -> None:
        self.calls = []
        self.output_payload = None

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return type("FakeResponse", (), {"output_text": json.dumps(self.output_payload)})()


class _FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = _FakeResponsesApi()


class OpenAIRuntimeSchemaTests(unittest.TestCase):
    def test_issue_planner_loader_wraps_array_schema_and_unwraps_response(self) -> None:
        fake_client = _FakeOpenAIClient()
        fake_client.responses.output_payload = {
            "items": [
                {
                    "issue_id": "issue_001",
                    "issue_question": "Will slower payroll growth shift Fed expectations?",
                    "thesis_hint": "Growth is cooling while policy stays cautious.",
                    "supporting_evidence_ids": ["chunk_001"],
                    "opposing_evidence_ids": ["chunk_002"],
                    "minority_evidence_ids": ["chunk_003"],
                    "watch_evidence_ids": ["chunk_004"],
                }
            ]
        }
        runtime_client = OpenAIResponsesTextClient(client=fake_client, model="gpt-4o-mini")
        planner = OpenAIIssuePlanner(response_loader=runtime_client.create_json_response)

        result = planner.plan_issues(
            brief_input=IssuePlannerInput(
                run_id="run_demo",
                generated_at_utc="2026-03-12T10:00:00Z",
                brief_plan={
                    "brief_id": "brief_2026-03-12",
                    "brief_thesis": "Growth is cooling while policy stays cautious.",
                    "top_takeaways": ["Growth cools.", "Policy stays cautious."],
                    "issue_budget": 2,
                    "render_mode": "full",
                    "source_scarcity_mode": "normal",
                    "candidate_issue_seeds": ["growth cooling", "policy caution"],
                    "issue_order": ["seed_001", "seed_002"],
                    "watchlist": ["Watch CPI."],
                    "reason_codes": ["two_distinct_debates_supported"],
                },
                issue_evidence_scopes=[
                    {
                        "issue_id": "issue_001",
                        "issue_seed": "growth cooling",
                        "primary_chunk_ids": ["chunk_001"],
                        "opposing_chunk_ids": ["chunk_002"],
                        "minority_chunk_ids": ["chunk_003"],
                        "watch_chunk_ids": ["chunk_004"],
                        "coverage_summary": {
                            "unique_publishers": 4,
                            "source_roles": ["official", "market_media"],
                            "time_span_hours": 12,
                        },
                    }
                ],
                prior_brief_context=None,
            )
        )

        self.assertEqual(result[0]["issue_id"], "issue_001")
        call = fake_client.responses.calls[0]
        self.assertEqual(call["text"]["format"]["schema"]["type"], "object")
        self.assertIn("items", call["text"]["format"]["schema"]["properties"])

    def test_claim_composer_loader_wraps_array_schema_and_unwraps_response(self) -> None:
        fake_client = _FakeOpenAIClient()
        fake_client.responses.output_payload = {
            "items": [
                {
                    "claim_id": "claim_001",
                    "issue_id": "issue_001",
                    "claim_kind": "prevailing",
                    "claim_text": "Slower growth is raising later-cut expectations.",
                    "supporting_citation_ids": ["cite_001"],
                    "opposing_citation_ids": [],
                    "confidence": "medium",
                    "novelty_vs_prior_brief": "new",
                    "why_it_matters": "Rate-sensitive assets can reprice quickly.",
                }
            ]
        }
        runtime_client = OpenAIResponsesTextClient(client=fake_client, model="gpt-4o-mini")
        composer = OpenAIClaimComposer(response_loader=runtime_client.create_json_response)

        result = composer.compose_claims(
            brief_input=ClaimComposerInput(
                run_id="run_demo",
                generated_at_utc="2026-03-12T10:00:00Z",
                issue_map=[
                    {
                        "issue_id": "issue_001",
                        "issue_question": "Will slower payroll growth shift Fed expectations?",
                        "thesis_hint": "Growth is cooling while policy stays cautious.",
                        "supporting_evidence_ids": ["chunk_001"],
                        "opposing_evidence_ids": ["chunk_002"],
                        "minority_evidence_ids": ["chunk_003"],
                        "watch_evidence_ids": ["chunk_004"],
                    }
                ],
                citation_store={
                    "cite_001": {
                        "citation_id": "cite_001",
                        "source_id": "reuters",
                        "publisher": "Reuters",
                        "doc_id": "doc_001",
                        "chunk_id": "chunk_001",
                        "url": "https://example.test/1",
                        "title": "Growth cools",
                        "published_at": "2026-03-12T09:00:00Z",
                        "fetched_at": "2026-03-12T09:05:00Z",
                        "paywall_policy": "full",
                        "quote_text": "Growth cools.",
                        "snippet_text": "Growth cools.",
                    }
                },
                prior_brief_context=None,
            )
        )

        self.assertEqual(result[0]["claim_id"], "claim_001")
        call = fake_client.responses.calls[0]
        self.assertEqual(call["text"]["format"]["schema"]["type"], "object")
        self.assertIn("items", call["text"]["format"]["schema"]["properties"])


if __name__ == "__main__":
    unittest.main()
