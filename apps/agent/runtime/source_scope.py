from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped,unused-ignore]

from apps.agent.pipeline.types import (
    SourceContentMode,
    SourceFetchVia,
    SourceRegistryEntry,
    SourceRole,
    SourceTimestampAuthority,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = ROOT / "artifacts" / "modelling" / "source_registry.yaml"
DEFAULT_ACTIVE_IDS_PATH = ROOT / "artifacts" / "runtime" / "v1_active_sources.yaml"


def load_source_registry(*, registry_path: Path | None = None) -> dict[str, SourceRegistryEntry]:
    path = registry_path or DEFAULT_REGISTRY_PATH
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    sources = payload.get("sources", [])
    return {
        str(source["id"]): _normalize_source_registry_entry(source)
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
            str(source_id): _normalize_source_registry_entry(source)
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


def _normalize_source_registry_entry(source: Mapping[str, Any]) -> SourceRegistryEntry:
    normalized = dict(source)
    _normalize_optional_enum_field(normalized, "fetch_via", SourceFetchVia)
    _normalize_optional_enum_field(normalized, "source_role", SourceRole)
    _normalize_optional_enum_field(normalized, "timestamp_authority", SourceTimestampAuthority)
    _normalize_optional_enum_field(normalized, "content_mode", SourceContentMode)
    return cast(SourceRegistryEntry, normalized)


def _normalize_optional_enum_field(
    payload: dict[str, Any],
    field_name: str,
    enum_type: type[SourceFetchVia]
    | type[SourceRole]
    | type[SourceTimestampAuthority]
    | type[SourceContentMode],
) -> None:
    value = payload.get(field_name)
    if value is None:
        return
    payload[field_name] = enum_type(str(value))
