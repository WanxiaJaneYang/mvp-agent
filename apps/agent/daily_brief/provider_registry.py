from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypeAlias, TypedDict

from apps.agent.daily_brief.model_interfaces import ClaimComposerProvider, IssuePlannerProvider

DailyBriefProviderName: TypeAlias = Literal["deterministic", "openai", "codex-oauth"]
RequestedDailyBriefProviderName: TypeAlias = Literal["auto", "deterministic", "openai", "codex-oauth"]
DailyBriefProviderMode: TypeAlias = Literal["deterministic", "model-assisted"]


class DailyBriefProviderResolution(TypedDict):
    requested_provider: RequestedDailyBriefProviderName | str
    resolved_provider: DailyBriefProviderName
    provider_mode: DailyBriefProviderMode
    provider_fallback_used: bool
    issue_planner: IssuePlannerProvider | None
    claim_composer: ClaimComposerProvider | None


def build_daily_brief_providers(
    *,
    provider: RequestedDailyBriefProviderName | str,
    openai_model: str | None = None,
    codex_runner: Callable[..., Any] | None = None,
    login_checker: Callable[[], bool] | None = None,
) -> tuple[IssuePlannerProvider | None, ClaimComposerProvider | None]:
    resolution = resolve_daily_brief_provider(
        provider=provider,
        openai_model=openai_model,
        codex_runner=codex_runner,
        login_checker=login_checker,
    )
    return (resolution["issue_planner"], resolution["claim_composer"])


def resolve_daily_brief_provider(
    *,
    provider: RequestedDailyBriefProviderName | str,
    openai_model: str | None = None,
    codex_runner: Callable[..., Any] | None = None,
    login_checker: Callable[[], bool] | None = None,
) -> DailyBriefProviderResolution:
    if provider == "auto":
        return _resolve_auto_provider(
            openai_model=openai_model,
            codex_runner=codex_runner,
            login_checker=login_checker,
        )
    if provider == "deterministic":
        return {
            "requested_provider": str(provider),
            "resolved_provider": "deterministic",
            "provider_mode": "deterministic",
            "provider_fallback_used": False,
            "issue_planner": None,
            "claim_composer": None,
        }
    if provider == "openai":
        issue_planner, claim_composer = _build_openai_providers(openai_model=openai_model)
        return {
            "requested_provider": str(provider),
            "resolved_provider": "openai",
            "provider_mode": "model-assisted",
            "provider_fallback_used": False,
            "issue_planner": issue_planner,
            "claim_composer": claim_composer,
        }
    if provider == "codex-oauth":
        issue_planner, claim_composer = _build_codex_oauth_providers(
            codex_runner=codex_runner,
            login_checker=login_checker,
        )
        return {
            "requested_provider": str(provider),
            "resolved_provider": "codex-oauth",
            "provider_mode": "model-assisted",
            "provider_fallback_used": False,
            "issue_planner": issue_planner,
            "claim_composer": claim_composer,
        }
    raise ValueError(f"Unsupported provider: {provider}")


def _resolve_auto_provider(
    *,
    openai_model: str | None,
    codex_runner: Callable[..., Any] | None,
    login_checker: Callable[[], bool] | None,
) -> DailyBriefProviderResolution:
    provider_errors: list[str] = []
    providers_to_try: tuple[DailyBriefProviderName, ...] = ("codex-oauth", "openai")
    for index, candidate in enumerate(providers_to_try):
        try:
            resolution = resolve_daily_brief_provider(
                provider=candidate,
                openai_model=openai_model,
                codex_runner=codex_runner,
                login_checker=login_checker,
            )
        except ValueError as exc:
            provider_errors.append(f"{candidate}: {exc}")
            continue
        return {
            **resolution,
            "requested_provider": "auto",
            "provider_fallback_used": index > 0,
        }

    joined_errors = "; ".join(provider_errors) if provider_errors else "no provider checks ran"
    raise ValueError(f"Auto provider resolution failed. Tried {joined_errors}.")


def _build_openai_providers(
    *,
    openai_model: str | None = None,
) -> tuple[IssuePlannerProvider, ClaimComposerProvider]:
    from apps.agent.daily_brief.openai_runtime import build_openai_daily_brief_providers

    builder_kwargs: dict[str, Any] = {}
    if openai_model is not None:
        builder_kwargs["model"] = openai_model
    return build_openai_daily_brief_providers(**builder_kwargs)


def _build_codex_oauth_providers(
    *,
    codex_runner: Callable[..., Any] | None = None,
    login_checker: Callable[[], bool] | None = None,
) -> tuple[IssuePlannerProvider, ClaimComposerProvider]:
    try:
        from apps.agent.daily_brief.codex_runtime import build_codex_daily_brief_providers
    except ImportError as exc:
        raise ValueError("codex-oauth provider requires apps.agent.daily_brief.codex_runtime.") from exc

    builder_kwargs: dict[str, Any] = {}
    if codex_runner is not None:
        builder_kwargs["codex_runner"] = codex_runner
    if login_checker is not None:
        builder_kwargs["login_checker"] = login_checker
    return build_codex_daily_brief_providers(**builder_kwargs)
