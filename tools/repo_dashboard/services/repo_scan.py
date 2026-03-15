from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COMMANDS: dict[str, dict[str, Any]] = {
    "fixture": {
        "id": "fixture",
        "label": "Fixture Demo",
        "argv": [
            "python",
            "scripts/run_daily_brief_fixture.py",
            "--base-dir",
            ".tmp_repo_dashboard/demo",
        ],
        "base_dir": ".tmp_repo_dashboard/demo",
    },
    "evals": {
        "id": "evals",
        "label": "Eval Suite",
        "argv": ["python", "evals/run_eval_suite.py"],
        "base_dir": None,
    },
    "targeted_tests": {
        "id": "targeted_tests",
        "label": "Targeted Tests",
        "argv": [
            "python",
            "-m",
            "unittest",
            "tests.agent.daily_brief.test_runner",
            "tests.agent.delivery.test_html_report",
            "tests.agent.validators.test_citation_validator",
            "-v",
        ],
        "base_dir": None,
    },
    "live": {
        "id": "live",
        "label": "Live Daily Brief",
        "argv": ["python", "scripts/run_daily_brief.py", "--base-dir", ".tmp_repo_dashboard/live"],
        "base_dir": ".tmp_repo_dashboard/live",
    },
}


def build_repo_overview(*, repo_root: Path) -> dict[str, Any]:
    modelling_root = repo_root / "artifacts" / "modelling"
    image_assets = _discover_image_assets(repo_root=repo_root)
    diagram_cards = [
        _card(
            card_id="architecture",
            title="Architecture",
            primary_path=modelling_root / "pipeline.md",
            assets=image_assets,
        ),
        _card(
            card_id="data_model",
            title="Data Model",
            primary_path=modelling_root / "data_model.md",
        ),
        _card(
            card_id="run_flow",
            title="Run Flow",
            primary_path=modelling_root / "decision_record_schema.md",
        ),
    ]
    return {
        "repo_name": repo_root.name,
        "repo_root": str(repo_root),
        "generated_at_utc": _utc_now_iso(),
        "diagram_cards": diagram_cards,
        "commands": COMMANDS,
    }


def _card(
    *,
    card_id: str,
    title: str,
    primary_path: Path,
    assets: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "id": card_id,
        "title": title,
        "primary_path": str(primary_path),
        "primary_uri": primary_path.resolve().as_uri() if primary_path.exists() else None,
        "assets": list(assets or []),
    }


def _discover_image_assets(*, repo_root: Path) -> list[dict[str, str]]:
    patterns = ("*.svg", "*.png")
    assets: list[dict[str, str]] = []
    search_roots = [repo_root / "artifacts", repo_root / "docs", repo_root]
    for pattern in patterns:
        for search_root in search_roots:
            if not search_root.exists():
                continue
            for path in search_root.rglob(pattern):
                asset = {
                    "label": path.name,
                    "kind": "image",
                    "path": str(path),
                    "uri": path.resolve().as_uri(),
                }
                if asset not in assets:
                    assets.append(asset)
    return assets


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
