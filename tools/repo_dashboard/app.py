from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from tools.repo_dashboard.services.artifact_reader import discover_dashboard_artifacts
from tools.repo_dashboard.services.command_runner import CommandRunner
from tools.repo_dashboard.services.repo_scan import build_repo_overview
from tools.repo_dashboard.services.status_store import DashboardStatusStore, default_health_entry

ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = Path(__file__).resolve().parent / "static"


class CommandRunnerProtocol(Protocol):
    def start_run(self, run_kind: str) -> dict[str, Any]:
        ...

    def latest_logs(self) -> dict[str, Any]:
        ...

    def refresh_active_run(self) -> None:
        ...


def create_app(
    *,
    repo_root: Path | None = None,
    data_dir: Path | None = None,
    command_runner: CommandRunnerProtocol | None = None,
) -> FastAPI:
    resolved_repo_root = repo_root or ROOT
    resolved_data_dir = data_dir or (resolved_repo_root / "tools" / "repo_dashboard" / "data")
    status_store = DashboardStatusStore(data_dir=resolved_data_dir)
    runner = command_runner or CommandRunner(
        repo_root=resolved_repo_root,
        data_dir=resolved_data_dir,
        status_store=status_store,
    )

    app = FastAPI(title="Repo Ops Dashboard")
    app.state.repo_root = resolved_repo_root
    app.state.data_dir = resolved_data_dir
    app.state.status_store = status_store
    app.state.command_runner = runner
    if STATIC_ROOT.exists():
        app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="repo-dashboard-static")

    @app.get("/", response_class=HTMLResponse)
    def dashboard_index() -> HTMLResponse:
        index_path = STATIC_ROOT / "index.html"
        return HTMLResponse(index_path.read_text(encoding="utf-8"))

    @app.get("/api/overview")
    def get_overview() -> dict[str, Any]:
        return _refresh_overview(app)

    @app.get("/api/health")
    def get_health() -> dict[str, Any]:
        return _refresh_health(app)

    @app.get("/api/latest-run")
    def get_latest_run() -> dict[str, Any]:
        _refresh_state(app)
        state = app.state.status_store.load_state()
        active_run_id = state.get("active_run_id")
        if isinstance(active_run_id, str):
            active_run = app.state.status_store.load_run(active_run_id)
            if active_run is not None:
                return active_run
        recent_runs = app.state.status_store.list_runs(limit=1)
        if recent_runs:
            return recent_runs[0]
        artifacts = discover_dashboard_artifacts(repo_root=app.state.repo_root)
        return artifacts["latest"]

    @app.get("/api/runs")
    def get_runs() -> list[dict[str, Any]]:
        app.state.command_runner.refresh_active_run()
        return app.state.status_store.list_runs()

    @app.get("/api/artifacts")
    def get_artifacts() -> dict[str, Any]:
        _refresh_state(app)
        return discover_dashboard_artifacts(repo_root=app.state.repo_root)

    @app.get("/api/logs/latest")
    def get_latest_logs() -> dict[str, Any]:
        return app.state.command_runner.latest_logs()

    @app.post("/api/run/fixture")
    def run_fixture() -> dict[str, Any]:
        return _start_run(app, "fixture")

    @app.post("/api/run/evals")
    def run_evals() -> dict[str, Any]:
        return _start_run(app, "evals")

    @app.post("/api/run/targeted-tests")
    def run_targeted_tests() -> dict[str, Any]:
        return _start_run(app, "targeted_tests")

    @app.post("/api/run/live")
    def run_live() -> dict[str, Any]:
        return _start_run(app, "live")

    @app.post("/api/refresh")
    def refresh() -> dict[str, Any]:
        overview = _refresh_overview(app)
        health = _refresh_health(app)
        return {"overview": overview, "health": health}

    _refresh_state(app)
    return app


def _start_run(app: FastAPI, run_kind: str) -> dict[str, Any]:
    try:
        record = app.state.command_runner.start_run(run_kind)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _refresh_health(app)
    return record


def _refresh_state(app: FastAPI) -> None:
    app.state.command_runner.refresh_active_run()
    _refresh_overview(app)
    _refresh_health(app)


def _refresh_overview(app: FastAPI) -> dict[str, Any]:
    overview = build_repo_overview(repo_root=app.state.repo_root)
    app.state.status_store.set_overview(overview)
    return overview


def _refresh_health(app: FastAPI) -> dict[str, Any]:
    status_store = app.state.status_store
    artifacts = discover_dashboard_artifacts(repo_root=app.state.repo_root)
    recent_runs = {run["run_kind"]: run for run in status_store.list_runs(limit=20)}
    health: dict[str, dict[str, Any]] = {}
    for run_kind in ("fixture", "evals", "targeted_tests", "live"):
        health_entry = default_health_entry(run_kind)
        run_record = recent_runs.get(run_kind)
        artifact_entry = artifacts["by_kind"].get(run_kind, {})
        if run_record is not None:
            health_entry.update(
                {
                    "status": run_record.get("status", health_entry["status"]),
                    "updated_at_utc": run_record.get("finished_at_utc") or run_record.get("started_at_utc"),
                    "artifact_paths": dict(run_record.get("artifact_paths", {})),
                    "publish_decision": run_record.get("publish_decision"),
                    "reason": run_record.get("reason"),
                    "reason_codes": list(run_record.get("reason_codes", [])),
                    "run_id": run_record.get("run_id"),
                }
            )
        if artifact_entry.get("updated_at_utc"):
            health_entry.update(
                {
                    "status": artifact_entry.get("status", health_entry["status"]),
                    "updated_at_utc": artifact_entry.get("updated_at_utc"),
                    "artifact_paths": dict(artifact_entry.get("artifact_paths", {})),
                    "publish_decision": artifact_entry.get("publish_decision"),
                    "reason": artifact_entry.get("reason"),
                    "reason_codes": list(artifact_entry.get("reason_codes", [])),
                    "brief_html_uri": artifact_entry.get("brief_html_uri"),
                    "decision_record_uri": artifact_entry.get("decision_record_uri"),
                }
            )
        health[run_kind] = health_entry
    status_store.set_health(health)
    return health


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("tools.repo_dashboard.app:app", host="127.0.0.1", port=8000, reload=False)
