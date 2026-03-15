from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from io import TextIOWrapper
from pathlib import Path
from typing import Any

from tools.repo_dashboard.services.artifact_reader import discover_dashboard_artifacts
from tools.repo_dashboard.services.repo_scan import COMMANDS
from tools.repo_dashboard.services.status_store import DashboardRunStatus, DashboardStatusStore


class CommandRunner:
    def __init__(self, *, repo_root: Path, data_dir: Path, status_store: DashboardStatusStore) -> None:
        self.repo_root = repo_root
        self.data_dir = data_dir
        self.status_store = status_store
        self._active_run_id: str | None = None
        self._active_run_kind: str | None = None
        self._active_log_path: Path | None = None
        self._active_log_handle: TextIOWrapper | None = None
        self._process: subprocess.Popen[str] | None = None
        self._started_at_utc: str | None = None

    def start_run(self, run_kind: str) -> dict[str, Any]:
        self.refresh_active_run()
        if self._process is not None and self._process.poll() is None:
            raise RuntimeError("A dashboard run is already active.")
        if run_kind not in COMMANDS:
            raise ValueError(f"Unknown dashboard run kind: {run_kind}")

        command = [str(item) for item in COMMANDS[run_kind]["argv"]]
        run_id = f"{run_kind}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        log_path = self.data_dir / "runs" / f"{run_id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"$ {' '.join(command)}\n", encoding="utf-8")

        log_handle = log_path.open("a", encoding="utf-8")
        process = subprocess.Popen(
            command,
            cwd=self.repo_root,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )

        self._process = process
        self._active_run_id = run_id
        self._active_run_kind = run_kind
        self._active_log_path = log_path
        self._active_log_handle = log_handle
        self._started_at_utc = _utc_now_iso()
        record = self.status_store.upsert_run(
            {
                "run_id": run_id,
                "run_kind": run_kind,
                "status": DashboardRunStatus.RUNNING.value,
                "command": command,
                "started_at_utc": self._started_at_utc,
                "finished_at_utc": None,
                "exit_code": None,
                "log_path": str(log_path),
                "base_dir": COMMANDS[run_kind]["base_dir"],
                "artifact_paths": {},
                "publish_decision": None,
                "reason": None,
                "reason_codes": [],
                "summary": None,
            },
            is_active=True,
        )
        return record

    def refresh_active_run(self) -> None:
        if self._process is None or self._active_run_id is None or self._active_run_kind is None:
            return
        exit_code = self._process.poll()
        if exit_code is None:
            return
        artifacts = discover_dashboard_artifacts(repo_root=self.repo_root)
        artifact_entry = artifacts["by_kind"].get(self._active_run_kind, {})
        status = DashboardRunStatus.OK.value if exit_code == 0 else DashboardRunStatus.FAILED.value
        self.status_store.upsert_run(
            {
                "run_id": self._active_run_id,
                "run_kind": self._active_run_kind,
                "status": status,
                "command": COMMANDS[self._active_run_kind]["argv"],
                "started_at_utc": self._started_at_utc or _utc_now_iso(),
                "finished_at_utc": _utc_now_iso(),
                "exit_code": exit_code,
                "log_path": "" if self._active_log_path is None else str(self._active_log_path),
                "base_dir": COMMANDS[self._active_run_kind]["base_dir"],
                "artifact_paths": dict(artifact_entry.get("artifact_paths", {})),
                "publish_decision": artifact_entry.get("publish_decision"),
                "reason": artifact_entry.get("reason"),
                "reason_codes": list(artifact_entry.get("reason_codes", [])),
                "summary": artifact_entry.get("reason"),
            },
            is_active=False,
        )
        self._process = None
        self._active_run_id = None
        self._active_run_kind = None
        self._active_log_path = None
        if self._active_log_handle is not None:
            self._active_log_handle.close()
            self._active_log_handle = None
        self._started_at_utc = None

    def latest_logs(self) -> dict[str, Any]:
        self.refresh_active_run()
        run_id = self._active_run_id
        if run_id is None:
            recent_runs = self.status_store.list_runs(limit=1)
            if recent_runs:
                run_id = str(recent_runs[0]["run_id"])
                log_path = Path(str(recent_runs[0]["log_path"]))
                return _tail_log(run_id=run_id, log_path=log_path, is_running=False)
            return {"run_id": None, "lines": [], "is_running": False, "log_path": None}
        return _tail_log(run_id=run_id, log_path=self._active_log_path, is_running=self._process is not None)


def _tail_log(*, run_id: str, log_path: Path | None, is_running: bool) -> dict[str, Any]:
    if log_path is None or not log_path.exists():
        return {"run_id": run_id, "lines": [], "is_running": is_running, "log_path": None}
    lines = log_path.read_text(encoding="utf-8").splitlines()[-200:]
    return {"run_id": run_id, "lines": lines, "is_running": is_running, "log_path": str(log_path)}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
