from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

from apps.agent.pipeline.types import ResolvedSource, SourceRegistryEntry

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = ROOT / "artifacts" / "modelling" / "source_registry.yaml"
DEFAULT_ACTIVE_IDS_PATH = ROOT / "artifacts" / "runtime" / "v1_active_sources.yaml"


def load_source_registry(*, registry_path: Path | None = None) -> dict[str, SourceRegistryEntry]:
    path = registry_path or DEFAULT_REGISTRY_PATH
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    sources = payload.get("sources", [])
    return {
        str(source["id"]): cast(SourceRegistryEntry, dict(source))
        for source in sources
    }


def load_active_source_subset(
    *,
    registry: Mapping[str, Mapping[str, Any]] | None = None,
    registry_path: Path | None = None,
    active_ids_path: Path | None = None,
) -> list[SourceRegistryEntry]:
    resolved_registry: dict[str, SourceRegistryEntry]
    if registry is not None:
        resolved_registry = {
            str(source_id): cast(SourceRegistryEntry, dict(source))
            for source_id, source in registry.items()
        }
    else:
        resolved_registry = load_source_registry(registry_path=registry_path)
    path = active_ids_path or DEFAULT_ACTIVE_IDS_PATH
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    active_source_ids = payload.get("active_source_ids", [])
    active_sources: list[SourceRegistryEntry] = []
    missing_ids: list[str] = []

    for source_id in active_source_ids:
        source = resolved_registry.get(str(source_id))
        if source is None:
            missing_ids.append(str(source_id))
            continue
        active_sources.append(cast(SourceRegistryEntry, dict(source)))

    if missing_ids:
        raise ValueError(f"Unknown active source ids: {', '.join(missing_ids)}")

    return active_sources


def load_runtime_eligible_sources(
    *,
    base_dir: Path,
    registry_path: Path | None = None,
) -> list[ResolvedSource]:
    from apps.agent.runtime.resolved_sources import load_resolved_sources

    return [
        source
        for source in load_resolved_sources(base_dir=base_dir, registry_path=registry_path)
        if source["runtime_eligible"]
    ]
