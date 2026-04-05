from __future__ import annotations

from pathlib import Path
from typing import cast

from apps.agent.pipeline.types import (
    ResolvedSource,
    SourceOnboardingRunRow,
    SourceOperatorStateRow,
    SourceRegistryEntry,
    SourceStrategyVersionRow,
)
from apps.agent.runtime.source_scope import load_source_registry
from apps.agent.storage.source_control_plane import SourceControlPlaneStore


def load_resolved_sources(
    *,
    base_dir: Path,
    registry_path: Path | None = None,
) -> list[ResolvedSource]:
    registry = load_source_registry(registry_path=registry_path)
    store = SourceControlPlaneStore(base_dir=base_dir)

    resolved: list[ResolvedSource] = []
    for source_id, contract in registry.items():
        operator_state = store.get_operator_state(source_id) or _default_operator_state(source_id)
        strategies = store.list_strategy_versions(source_id)
        onboarding_runs = store.list_onboarding_runs(source_id)
        current_strategy = _pick_current_strategy(operator_state=operator_state, strategies=strategies)
        latest_strategy = strategies[0] if strategies else None
        latest_onboarding_run = onboarding_runs[0] if onboarding_runs else None
        resolved.append(
            ResolvedSource(
                source_id=source_id,
                contract=_with_contract_fallbacks(contract),
                operator_state=operator_state,
                current_strategy=current_strategy,
                latest_strategy=latest_strategy,
                latest_onboarding_run=latest_onboarding_run,
                runtime_eligible=_is_runtime_eligible(
                    operator_state=operator_state,
                    current_strategy=current_strategy,
                ),
            )
        )
    return resolved


def get_resolved_source(
    source_id: str,
    *,
    base_dir: Path,
    registry_path: Path | None = None,
) -> ResolvedSource:
    for source in load_resolved_sources(base_dir=base_dir, registry_path=registry_path):
        if source["source_id"] == source_id:
            return source
    raise ValueError(f"Unknown source id: {source_id}")


def _default_operator_state(source_id: str) -> SourceOperatorStateRow:
    return SourceOperatorStateRow(
        source_id=source_id,
        is_active=0,
        strategy_state="missing",
        current_strategy_id=None,
        latest_strategy_id=None,
        last_onboarding_run_id=None,
        last_collection_status="idle",
        last_collection_started_at=None,
        last_collection_finished_at=None,
        last_collection_error=None,
        activated_at=None,
        deactivated_at=None,
        updated_at="",
    )


def _pick_current_strategy(
    *,
    operator_state: SourceOperatorStateRow,
    strategies: list[SourceStrategyVersionRow],
) -> SourceStrategyVersionRow | None:
    current_strategy_id = operator_state["current_strategy_id"]
    if current_strategy_id is None:
        return None
    for strategy in strategies:
        if strategy["strategy_id"] == current_strategy_id:
            return strategy
    return None


def _is_runtime_eligible(
    *,
    operator_state: SourceOperatorStateRow,
    current_strategy: SourceStrategyVersionRow | None,
) -> bool:
    return (
        bool(operator_state["is_active"])
        and operator_state["strategy_state"] == "ready"
        and operator_state["current_strategy_id"] is not None
        and current_strategy is not None
        and current_strategy["strategy_status"] == "approved"
    )


def _with_contract_fallbacks(source: SourceRegistryEntry) -> SourceRegistryEntry:
    normalized = dict(source)
    normalized.setdefault("fetch_via", _default_fetch_via(str(source["type"])))
    normalized.setdefault("source_role", "authoritative")
    normalized.setdefault("timestamp_authority", "source_page")
    normalized.setdefault("content_mode", _default_content_mode(str(source["type"])))
    return cast(SourceRegistryEntry, normalized)


def _default_fetch_via(source_type: str) -> str:
    if source_type == "rss":
        return "direct_rss"
    if source_type == "html":
        return "direct_html"
    if source_type == "pdf":
        return "direct_pdf"
    return "hybrid"


def _default_content_mode(source_type: str) -> str:
    if source_type == "pdf":
        return "article_full_text"
    if source_type == "rss":
        return "feed_index"
    return "article_full_text"
