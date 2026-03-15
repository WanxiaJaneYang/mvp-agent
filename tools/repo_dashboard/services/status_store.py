from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

SUPPORTED_RUN_KINDS = ("fixture", "evals", "targeted_tests", "live")


class DashboardRunStatus(str, Enum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class DashboardRunRecord:
    run_id: str
    run_kind: str
    status: str
    command: list[str]
    started_at_utc: str
    finished_at_utc: str | None
    exit_code: int | None
    log_path: str
    base_dir: str | None
    artifact_paths: dict[str, str] = field(default_factory=dict)
    publish_decision: str | None = None
    reason: str | None = None
    reason_codes: list[str] = field(default_factory=list)
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_health_entry(run_kind: str) -> dict[str, Any]:
    return {
        "run_kind": run_kind,
        "status": DashboardRunStatus.IDLE.value,
        "publish_decision": None,
        "reason": None,
        "reason_codes": [],
        "updated_at_utc": None,
        "artifact_paths": {},
    }


def default_state_payload() -> dict[str, Any]:
    return {
        "active_run_id": None,
        "overview": {},
        "health": {run_kind: default_health_entry(run_kind) for run_kind in SUPPORTED_RUN_KINDS},
        "recent_runs": [],
    }


class DashboardStatusStore:
    def __init__(self, *, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.state_path = self.data_dir / "dashboard_state.json"
        self.runs_dir = self.data_dir / "runs"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self.state_path.write_text(json.dumps(default_state_payload(), indent=2), encoding="utf-8")

    def load_state(self) -> dict[str, Any]:
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        state = default_state_payload()
        state.update(payload)
        health = dict(state["health"])
        for run_kind in SUPPORTED_RUN_KINDS:
            health.setdefault(run_kind, default_health_entry(run_kind))
        state["health"] = health
        recent_runs = state.get("recent_runs", [])
        state["recent_runs"] = recent_runs if isinstance(recent_runs, list) else []
        return state

    def save_state(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        state = default_state_payload()
        state.update(dict(payload))
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return state

    def list_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        state = self.load_state()
        runs = [self.load_run(str(item["run_id"])) for item in state.get("recent_runs", []) if item.get("run_id")]
        return [run for run in runs if run is not None][:limit]

    def load_run(self, run_id: str) -> dict[str, Any] | None:
        run_path = self.runs_dir / f"{run_id}.json"
        if not run_path.exists():
            return None
        return json.loads(run_path.read_text(encoding="utf-8"))

    def upsert_run(self, run_record: Mapping[str, Any], *, is_active: bool = False) -> dict[str, Any]:
        normalized = DashboardRunRecord(
            run_id=str(run_record["run_id"]),
            run_kind=str(run_record["run_kind"]),
            status=str(run_record["status"]),
            command=[str(item) for item in run_record.get("command", [])],
            started_at_utc=str(run_record["started_at_utc"]),
            finished_at_utc=None if run_record.get("finished_at_utc") is None else str(run_record["finished_at_utc"]),
            exit_code=None if run_record.get("exit_code") is None else int(run_record["exit_code"]),
            log_path=str(run_record["log_path"]),
            base_dir=None if run_record.get("base_dir") is None else str(run_record["base_dir"]),
            artifact_paths={str(key): str(value) for key, value in dict(run_record.get("artifact_paths", {})).items()},
            publish_decision=None
            if run_record.get("publish_decision") is None
            else str(run_record["publish_decision"]),
            reason=None if run_record.get("reason") is None else str(run_record["reason"]),
            reason_codes=[str(code) for code in run_record.get("reason_codes", [])],
            summary=None if run_record.get("summary") is None else str(run_record["summary"]),
        ).to_dict()

        run_path = self.runs_dir / f"{normalized['run_id']}.json"
        run_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")

        state = self.load_state()
        recent_runs = [item for item in state["recent_runs"] if item.get("run_id") != normalized["run_id"]]
        recent_runs.insert(
            0,
            {
                "run_id": normalized["run_id"],
                "run_kind": normalized["run_kind"],
                "status": normalized["status"],
                "started_at_utc": normalized["started_at_utc"],
                "finished_at_utc": normalized["finished_at_utc"],
            },
        )
        state["recent_runs"] = recent_runs[:20]
        if is_active:
            state["active_run_id"] = normalized["run_id"]
        elif state["active_run_id"] == normalized["run_id"] and normalized["status"] != DashboardRunStatus.RUNNING.value:
            state["active_run_id"] = None
        self.save_state(state)
        return normalized

    def set_overview(self, overview: Mapping[str, Any]) -> dict[str, Any]:
        state = self.load_state()
        state["overview"] = dict(overview)
        self.save_state(state)
        return state["overview"]

    def set_health(self, health: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        state = self.load_state()
        state["health"] = {run_kind: dict(payload) for run_kind, payload in health.items()}
        self.save_state(state)
        return state["health"]
