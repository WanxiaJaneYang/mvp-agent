from __future__ import annotations

import json
from pathlib import Path

import yaml


def main() -> None:
    json_paths = [
        Path("artifacts/modelling/backlog.json"),
    ]
    yaml_paths = [
        Path("artifacts/modelling/source_registry.yaml"),
    ]

    for path in json_paths:
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)

    for path in yaml_paths:
        with path.open("r", encoding="utf-8") as handle:
            yaml.safe_load(handle)

    print("Artifact validation passed.")


if __name__ == "__main__":
    main()
