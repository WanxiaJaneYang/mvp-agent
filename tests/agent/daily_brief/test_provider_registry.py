from __future__ import annotations

import sys
import unittest
from unittest.mock import patch


class ProviderRegistryTests(unittest.TestCase):
    def test_resolve_daily_brief_provider_returns_deterministic_metadata(self):
        from apps.agent.daily_brief.provider_registry import resolve_daily_brief_provider

        resolution = resolve_daily_brief_provider(provider="deterministic")

        self.assertEqual(resolution["requested_provider"], "deterministic")
        self.assertEqual(resolution["resolved_provider"], "deterministic")
        self.assertEqual(resolution["provider_mode"], "deterministic")
        self.assertFalse(resolution["provider_fallback_used"])
        self.assertIsNone(resolution["issue_planner"])
        self.assertIsNone(resolution["claim_composer"])

    def test_build_daily_brief_providers_returns_none_for_deterministic(self):
        from apps.agent.daily_brief.provider_registry import build_daily_brief_providers

        issue_planner, claim_composer = build_daily_brief_providers(provider="deterministic")

        self.assertIsNone(issue_planner)
        self.assertIsNone(claim_composer)

    def test_build_daily_brief_providers_delegates_openai_builder(self):
        from apps.agent.daily_brief import provider_registry

        planner = object()
        composer = object()

        with patch.object(
            provider_registry,
            "_build_openai_providers",
            return_value=(planner, composer),
        ) as openai_mock:
            issue_planner, claim_composer = provider_registry.build_daily_brief_providers(
                provider="openai",
                openai_model="gpt-test",
            )

        openai_mock.assert_called_once_with(openai_model="gpt-test")
        self.assertIs(issue_planner, planner)
        self.assertIs(claim_composer, composer)

    def test_build_daily_brief_providers_delegates_codex_oauth_builder(self):
        from apps.agent.daily_brief import provider_registry

        planner = object()
        composer = object()
        fake_runner = object()

        with patch.object(
            provider_registry,
            "_build_codex_oauth_providers",
            return_value=(planner, composer),
        ) as codex_mock:
            issue_planner, claim_composer = provider_registry.build_daily_brief_providers(
                provider="codex-oauth",
                codex_runner=fake_runner,
            )

        codex_mock.assert_called_once_with(codex_runner=fake_runner, login_checker=None)
        self.assertIs(issue_planner, planner)
        self.assertIs(claim_composer, composer)

    def test_build_daily_brief_providers_rejects_unknown_provider(self):
        from apps.agent.daily_brief.provider_registry import build_daily_brief_providers

        with self.assertRaisesRegex(ValueError, "Unsupported provider"):
            build_daily_brief_providers(provider="unsupported")

    def test_resolve_daily_brief_provider_auto_prefers_codex_oauth(self):
        from apps.agent.daily_brief import provider_registry

        planner = object()
        composer = object()

        with (
            patch.object(
                provider_registry,
                "_build_codex_oauth_providers",
                return_value=(planner, composer),
            ) as codex_mock,
            patch.object(provider_registry, "_build_openai_providers") as openai_mock,
        ):
            resolution = provider_registry.resolve_daily_brief_provider(provider="auto")

        codex_mock.assert_called_once_with(codex_runner=None, login_checker=None)
        openai_mock.assert_not_called()
        self.assertEqual(resolution["requested_provider"], "auto")
        self.assertEqual(resolution["resolved_provider"], "codex-oauth")
        self.assertEqual(resolution["provider_mode"], "model-assisted")
        self.assertFalse(resolution["provider_fallback_used"])
        self.assertIs(resolution["issue_planner"], planner)
        self.assertIs(resolution["claim_composer"], composer)

    def test_resolve_daily_brief_provider_auto_falls_back_to_openai(self):
        from apps.agent.daily_brief import provider_registry

        planner = object()
        composer = object()

        with (
            patch.object(
                provider_registry,
                "_build_codex_oauth_providers",
                side_effect=ValueError("codex unavailable"),
            ) as codex_mock,
            patch.object(
                provider_registry,
                "_build_openai_providers",
                return_value=(planner, composer),
            ) as openai_mock,
        ):
            resolution = provider_registry.resolve_daily_brief_provider(
                provider="auto",
                openai_model="gpt-test",
            )

        codex_mock.assert_called_once_with(codex_runner=None, login_checker=None)
        openai_mock.assert_called_once_with(openai_model="gpt-test")
        self.assertEqual(resolution["resolved_provider"], "openai")
        self.assertEqual(resolution["provider_mode"], "model-assisted")
        self.assertTrue(resolution["provider_fallback_used"])

    def test_resolve_daily_brief_provider_auto_fails_closed_when_none_available(self):
        from apps.agent.daily_brief import provider_registry

        with (
            patch.object(
                provider_registry,
                "_build_codex_oauth_providers",
                side_effect=ValueError("codex unavailable"),
            ),
            patch.object(
                provider_registry,
                "_build_openai_providers",
                side_effect=ValueError("openai unavailable"),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "Auto provider resolution failed"):
                provider_registry.resolve_daily_brief_provider(provider="auto")


class RunnerScriptProviderWiringTests(unittest.TestCase):
    def test_fixture_script_defaults_to_deterministic(self):
        from scripts import run_daily_brief_fixture

        with patch.object(sys, "argv", ["run_daily_brief_fixture.py"]):
            args = run_daily_brief_fixture.parse_args()

        self.assertEqual(args.provider, "deterministic")

    def test_fixture_script_accepts_codex_oauth_provider(self):
        from scripts import run_daily_brief_fixture

        with patch.object(sys, "argv", ["run_daily_brief_fixture.py", "--provider", "codex-oauth"]):
            args = run_daily_brief_fixture.parse_args()

        self.assertEqual(args.provider, "codex-oauth")

    def test_fixture_script_resolves_providers_through_registry(self):
        from scripts import run_daily_brief_fixture

        planner = object()
        composer = object()
        resolution = {
            "requested_provider": "openai",
            "resolved_provider": "openai",
            "provider_mode": "model-assisted",
            "provider_fallback_used": False,
            "issue_planner": planner,
            "claim_composer": composer,
        }

        with (
            patch(
                "apps.agent.daily_brief.provider_registry.resolve_daily_brief_provider",
                return_value=resolution,
            ) as registry_mock,
            patch(
                "apps.agent.daily_brief.runner.run_fixture_daily_brief",
                return_value={"status": "ok", "run_id": "run_fixture"},
            ) as runner_mock,
            patch.object(
                sys,
                "argv",
                [
                    "run_daily_brief_fixture.py",
                    "--provider",
                    "openai",
                    "--openai-model",
                    "gpt-test",
                ],
            ),
        ):
            run_daily_brief_fixture.main()

        registry_mock.assert_called_once_with(provider="openai", openai_model="gpt-test")
        self.assertIs(runner_mock.call_args.kwargs["issue_planner"], planner)
        self.assertIs(runner_mock.call_args.kwargs["claim_composer"], composer)
        self.assertEqual(runner_mock.call_args.kwargs["provider_resolution"], resolution)

    def test_live_script_defaults_to_auto(self):
        from scripts import run_daily_brief

        with patch.object(sys, "argv", ["run_daily_brief.py"]):
            args = run_daily_brief.parse_args()

        self.assertEqual(args.provider, "auto")

    def test_live_script_accepts_codex_oauth_provider(self):
        from scripts import run_daily_brief

        with patch.object(sys, "argv", ["run_daily_brief.py", "--provider", "codex-oauth"]):
            args = run_daily_brief.parse_args()

        self.assertEqual(args.provider, "codex-oauth")

    def test_live_script_resolves_providers_through_registry(self):
        from scripts import run_daily_brief

        planner = object()
        composer = object()
        resolution = {
            "requested_provider": "auto",
            "resolved_provider": "openai",
            "provider_mode": "model-assisted",
            "provider_fallback_used": True,
            "issue_planner": planner,
            "claim_composer": composer,
        }

        with (
            patch(
                "apps.agent.daily_brief.provider_registry.resolve_daily_brief_provider",
                return_value=resolution,
            ) as registry_mock,
            patch(
                "apps.agent.daily_brief.runner.run_daily_brief",
                return_value={"status": "ok", "run_id": "run_live"},
            ) as runner_mock,
            patch.object(
                sys,
                "argv",
                [
                    "run_daily_brief.py",
                    "--openai-model",
                    "gpt-live",
                ],
            ),
        ):
            run_daily_brief.main()

        registry_mock.assert_called_once_with(provider="auto", openai_model="gpt-live")
        self.assertIs(runner_mock.call_args.kwargs["issue_planner"], planner)
        self.assertIs(runner_mock.call_args.kwargs["claim_composer"], composer)
        self.assertEqual(runner_mock.call_args.kwargs["provider_resolution"], resolution)


if __name__ == "__main__":
    unittest.main()
