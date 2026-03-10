from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = ROOT / "artifacts" / "modelling" / "source_registry.yaml"
DEFAULT_ACTIVE_IDS_PATH = ROOT / "artifacts" / "runtime" / "v1_active_sources.yaml"


def load_source_registry(*, registry_path: Path | None = None) -> dict[str, dict[str, Any]]:
    path = registry_path or DEFAULT_REGISTRY_PATH
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    sources = payload.get("sources", [])
    return {str(source["id"]): dict(source) for source in sources}


def load_active_source_subset(
    *,
    registry: Mapping[str, Mapping[str, Any]] | None = None,
    registry_path: Path | None = None,
    active_ids_path: Path | None = None,
) -> list[dict[str, Any]]:
    resolved_registry = dict(registry) if registry is not None else load_source_registry(registry_path=registry_path)
    path = active_ids_path or DEFAULT_ACTIVE_IDS_PATH
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    active_source_ids = payload.get("active_source_ids", [])
    active_sources: list[dict[str, Any]] = []
    missing_ids: list[str] = []

    for source_id in active_source_ids:
        source = resolved_registry.get(str(source_id))
        if source is None:
            missing_ids.append(str(source_id))
            continue
        active_sources.append(dict(source))

    if missing_ids:
        raise ValueError(f"Unknown active source ids: {', '.join(missing_ids)}")

    return active_sources
