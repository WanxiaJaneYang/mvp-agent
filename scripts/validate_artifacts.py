from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TICKET_ID_PATTERN = re.compile(r"M\d{3}")


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError as error:
                raise json.JSONDecodeError(
                    f"{error.msg} (while parsing {path})",
                    error.doc,
                    error.pos,
                ) from error
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Required JSON artifact file not found: {path}") from error


def _load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            try:
                return yaml.safe_load(handle)
            except yaml.YAMLError as error:
                raise yaml.YAMLError(f"{error} (while parsing {path})") from error
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Required YAML artifact file not found: {path}") from error


def validate_backlog_ticket_paths(backlog: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []

    for ticket in backlog.get("tickets", []):
        ticket_id = ticket.get("id", "<unknown>")
        status = ticket.get("status")
        files = ticket.get("files", [])
        existing_paths = [(repo_root / relative_path).exists() for relative_path in files]

        if status == "implemented" and not all(existing_paths):
            missing_files = [path for path in files if not (repo_root / path).exists()]
            errors.append(
                "Backlog ticket "
                f"{ticket_id} is marked implemented but missing listed files: "
                f"{', '.join(missing_files)}."
            )
        if status == "planned" and files and all(existing_paths):
            errors.append(
                f"Backlog ticket {ticket_id} is marked planned even though all listed files exist."
            )

    return errors


def validate_status_matrix(status_matrix_text: str, backlog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ticket_statuses = {
        ticket["id"]: ticket["status"] for ticket in backlog.get("tickets", []) if "id" in ticket
    }

    for raw_line in status_matrix_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or "---" in line:
            continue

        columns = [column.strip() for column in line.strip("|").split("|")]
        if len(columns) != 5:
            continue

        coded = columns[2].lower()
        verified = columns[3].lower()
        evidence = columns[4]

        for ticket_id in TICKET_ID_PATTERN.findall(evidence):
            status = ticket_statuses.get(ticket_id)
            if status == "planned" and (coded != "no" or verified != "no"):
                errors.append(
                    "docs/status-matrix.md row for ticket "
                    f"{ticket_id} must report coded=no and verified=no while backlog status is planned."
                )
            if status == "implemented" and (coded != "yes" or verified != "yes"):
                errors.append(
                    "docs/status-matrix.md row for ticket "
                    f"{ticket_id} must report coded=yes and verified=yes while backlog status is implemented."
                )

    return errors


def validate_readme_status(readme_text: str, backlog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ticket_statuses = {
        ticket["id"]: ticket["status"] for ticket in backlog.get("tickets", []) if "id" in ticket
    }
    lower_text = readme_text.lower()

    alerts_planned = any(
        ticket_statuses.get(ticket_id) != "implemented" for ticket_id in ("M006", "M010")
    )
    if alerts_planned and "major-event alerts" in lower_text and "remain planned" not in lower_text:
        errors.append(
            "README.md must mark alerts as planned until backlog tickets M006 and M010 are implemented."
        )

    return errors


def validate_repo_artifacts(repo_root: Path = ROOT) -> list[str]:
    json_paths = [
        repo_root / "artifacts/modelling/backlog.json",
    ]
    yaml_paths = [
        repo_root / "artifacts/modelling/source_registry.yaml",
        repo_root / "artifacts/runtime/v1_active_sources.yaml",
    ]

    loaded_json: dict[Path, Any] = {}
    for path in json_paths:
        loaded_json[path] = _load_json(path)

    for path in yaml_paths:
        _load_yaml(path)

    backlog = loaded_json[repo_root / "artifacts/modelling/backlog.json"]
    status_matrix_text = (repo_root / "docs/status-matrix.md").read_text(encoding="utf-8")
    readme_text = (repo_root / "README.md").read_text(encoding="utf-8")

    errors: list[str] = []
    errors.extend(validate_backlog_ticket_paths(backlog, repo_root))
    errors.extend(validate_status_matrix(status_matrix_text, backlog))
    errors.extend(validate_readme_status(readme_text, backlog))
    return errors


def main() -> int:
    errors = validate_repo_artifacts()
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Artifact validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
