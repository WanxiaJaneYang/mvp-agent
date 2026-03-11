from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypeAlias

from apps.agent.daily_brief.model_interfaces import ClaimComposerProvider, IssuePlannerProvider

DailyBriefProviderName: TypeAlias = Literal["deterministic", "openai", "codex-oauth"]


def build_daily_brief_providers(
    *,
    provider: DailyBriefProviderName | str,
    openai_model: str | None = None,
    codex_runner: Callable[..., Any] | None = None,
    login_checker: Callable[[], bool] | None = None,
) -> tuple[IssuePlannerProvider | None, ClaimComposerProvider | None]:
    if provider == "deterministic":
        return (None, None)
    if provider == "openai":
        return _build_openai_providers(openai_model=openai_model)
    if provider == "codex-oauth":
        return _build_codex_oauth_providers(
            codex_runner=codex_runner,
            login_checker=login_checker,
        )
    raise ValueError(f"Unsupported provider: {provider}")


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
