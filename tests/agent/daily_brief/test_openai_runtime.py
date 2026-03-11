import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from apps.agent.daily_brief.openai_claim_composer import OpenAIClaimComposer
from apps.agent.daily_brief.openai_issue_planner import OpenAIIssuePlanner
from apps.agent.daily_brief.openai_runtime import (
    DEFAULT_OPENAI_MODEL,
    OpenAIResponsesTextClient,
    build_openai_daily_brief_providers,
)


class _FakeResponsesApi:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        payload = json.dumps(
            [
                {
                    "issue_id": "issue_001",
                    "issue_question": "Will growth slow enough to change Fed expectations?",
                    "thesis_hint": "Growth is cooling while inflation remains uneven.",
                    "supporting_evidence_ids": ["chunk_001"],
                    "opposing_evidence_ids": ["chunk_002"],
                    "minority_evidence_ids": ["chunk_003"],
                    "watch_evidence_ids": ["chunk_004"],
                }
            ]
        )
        return type("FakeResponse", (), {"output_text": payload})()


class _FakeOpenAIClient:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.responses = _FakeResponsesApi()


class OpenAIRuntimeTests(unittest.TestCase):
    def test_build_openai_daily_brief_providers_requires_api_key(self) -> None:
        with self.assertRaises(ValueError):
            build_openai_daily_brief_providers(api_key=None, client_factory=_FakeOpenAIClient)

    def test_build_openai_daily_brief_providers_returns_runtime_backed_adapters(self) -> None:
        planner, composer = build_openai_daily_brief_providers(
            api_key="test-key",
            model="gpt-4o-mini",
            client_factory=_FakeOpenAIClient,
        )

        self.assertIsInstance(planner, OpenAIIssuePlanner)
        self.assertIsInstance(composer, OpenAIClaimComposer)

    def test_openai_responses_text_client_translates_request_payload(self) -> None:
        fake_client = _FakeOpenAIClient(api_key="test-key")
        runtime_client = OpenAIResponsesTextClient(client=fake_client, model="gpt-4o-mini")

        output_text = runtime_client.create_json_response(
            {
                "messages": [
                    {"role": "system", "content": "Plan issue-centered topics."},
                    {"role": "user", "content": "Return strict JSON."},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "issue_map_list",
                        "strict": True,
                        "schema": {"type": "array"},
                    },
                },
            }
        )

        self.assertIn('"issue_id": "issue_001"', output_text)
        call = fake_client.responses.calls[0]
        self.assertEqual(call["model"], "gpt-4o-mini")
        self.assertEqual(call["instructions"], "Plan issue-centered topics.")
        self.assertEqual(call["input"], [{"role": "user", "content": "Return strict JSON."}])
        self.assertEqual(call["text"]["format"]["type"], "json_schema")
        self.assertEqual(call["text"]["format"]["name"], "issue_map_list")
        self.assertTrue(call["text"]["format"]["strict"])

    def test_fixture_script_fails_clearly_when_openai_provider_requested_without_key(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        script_path = repo_root / "scripts" / "run_daily_brief_fixture.py"
        env = dict(os.environ)
        env.pop("OPENAI_API_KEY", None)

        with tempfile.TemporaryDirectory() as tmpdir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--base-dir",
                    tmpdir,
                    "--provider",
                    "openai",
                    "--openai-model",
                    DEFAULT_OPENAI_MODEL,
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("OPENAI_API_KEY", completed.stderr)


if __name__ == "__main__":
    unittest.main()
