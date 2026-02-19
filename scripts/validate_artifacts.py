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
        try:
            with path.open("r", encoding="utf-8") as handle:
                try:
                    json.load(handle)
                except json.JSONDecodeError as error:
                    raise json.JSONDecodeError(
                        f"{error.msg} (while parsing {path})",
                        error.doc,
                        error.pos,
                    ) from error
        except FileNotFoundError as error:
            raise FileNotFoundError(f"Required JSON artifact file not found: {path}") from error

    for path in yaml_paths:
        try:
            with path.open("r", encoding="utf-8") as handle:
                try:
                    yaml.safe_load(handle)
                except yaml.YAMLError as error:
                    raise yaml.YAMLError(f"{error} (while parsing {path})") from error
        except FileNotFoundError as error:
            raise FileNotFoundError(f"Required YAML artifact file not found: {path}") from error

    print("Artifact validation passed.")


if __name__ == "__main__":
    main()
