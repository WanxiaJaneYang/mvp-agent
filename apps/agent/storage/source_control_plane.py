from __future__ import annotations

import sqlite3
from pathlib import Path

from apps.agent.pipeline.types import SourceOperatorStateRow


def control_plane_db_path(*, base_dir: Path) -> Path:
    runtime_dir = base_dir / "artifacts" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / "source_control_plane.sqlite3"


def ensure_control_plane_db(*, base_dir: Path) -> Path:
    db_path = control_plane_db_path(base_dir=base_dir)
    connection = sqlite3.connect(db_path)
    try:
        _initialize_schema(connection)
        connection.commit()
    finally:
        connection.close()
    return db_path


class SourceControlPlaneStore:
    def __init__(self, *, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.db_path = ensure_control_plane_db(base_dir=base_dir)

    def get_operator_state(self, source_id: str) -> SourceOperatorStateRow | None:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT
                  source_id,
                  is_active,
                  strategy_state,
                  current_strategy_id,
                  latest_strategy_id,
                  last_onboarding_run_id,
                  last_collection_status,
                  last_collection_started_at,
                  last_collection_finished_at,
                  last_collection_error,
                  activated_at,
                  deactivated_at,
                  updated_at
                FROM source_operator_state
                WHERE source_id = ?
                """,
                (source_id,),
            ).fetchone()
        finally:
            connection.close()

        if row is None:
            return None
        return SourceOperatorStateRow(
            source_id=str(row["source_id"]),
            is_active=int(row["is_active"]),
            strategy_state=str(row["strategy_state"]),
            current_strategy_id=None
            if row["current_strategy_id"] is None
            else str(row["current_strategy_id"]),
            latest_strategy_id=None if row["latest_strategy_id"] is None else str(row["latest_strategy_id"]),
            last_onboarding_run_id=None
            if row["last_onboarding_run_id"] is None
            else str(row["last_onboarding_run_id"]),
            last_collection_status=str(row["last_collection_status"]),
            last_collection_started_at=None
            if row["last_collection_started_at"] is None
            else str(row["last_collection_started_at"]),
            last_collection_finished_at=None
            if row["last_collection_finished_at"] is None
            else str(row["last_collection_finished_at"]),
            last_collection_error=None
            if row["last_collection_error"] is None
            else str(row["last_collection_error"]),
            activated_at=None if row["activated_at"] is None else str(row["activated_at"]),
            deactivated_at=None if row["deactivated_at"] is None else str(row["deactivated_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    statements = (
        """
        CREATE TABLE IF NOT EXISTS source_operator_state (
          source_id TEXT PRIMARY KEY,
          is_active INTEGER NOT NULL DEFAULT 0,
          strategy_state TEXT NOT NULL DEFAULT 'missing',
          current_strategy_id TEXT,
          latest_strategy_id TEXT,
          last_onboarding_run_id TEXT,
          last_collection_status TEXT NOT NULL DEFAULT 'idle',
          last_collection_started_at TEXT,
          last_collection_finished_at TEXT,
          last_collection_error TEXT,
          activated_at TEXT,
          deactivated_at TEXT,
          updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS source_strategy_versions (
          strategy_id TEXT PRIMARY KEY,
          source_id TEXT NOT NULL,
          version INTEGER NOT NULL,
          strategy_status TEXT NOT NULL,
          entrypoint_url TEXT NOT NULL,
          fetch_via TEXT NOT NULL,
          content_mode TEXT NOT NULL,
          parser_profile TEXT,
          max_items_per_run INTEGER NOT NULL,
          strategy_summary_json TEXT NOT NULL,
          strategy_details_json TEXT NOT NULL,
          created_from_run_id TEXT,
          created_at TEXT NOT NULL,
          approved_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS source_onboarding_runs (
          onboarding_run_id TEXT PRIMARY KEY,
          source_id TEXT NOT NULL,
          status TEXT NOT NULL,
          worker_kind TEXT NOT NULL,
          worker_ref TEXT,
          submitted_at TEXT NOT NULL,
          started_at TEXT,
          finished_at TEXT,
          proposed_strategy_id TEXT,
          error_message TEXT,
          result_summary_json TEXT
        )
        """,
    )
    for statement in statements:
        connection.execute(statement)
