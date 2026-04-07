from __future__ import annotations

import sqlite3
from pathlib import Path

from apps.agent.pipeline.types import (
    SOURCE_COLLECTION_STATUS_VALUES,
    SOURCE_ONBOARDING_RUN_STATUS_VALUES,
    SOURCE_STRATEGY_STATE_VALUES,
    SOURCE_STRATEGY_STATUS_VALUES,
    SourceCollectionStatus,
    SourceContentMode,
    SourceFetchVia,
    SourceOnboardingRunRow,
    SourceOnboardingRunStatus,
    SourceOperatorStateRow,
    SourceStrategyState,
    SourceStrategyStatus,
    SourceStrategyVersionRow,
)


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

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

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
        return _row_to_operator_state(row)

    def list_operator_states(self) -> list[SourceOperatorStateRow]:
        connection = self._connect()
        try:
            rows = connection.execute(
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
                ORDER BY source_id ASC
                """
            ).fetchall()
        finally:
            connection.close()
        return [_row_to_operator_state(row) for row in rows]

    def upsert_operator_state(self, row: SourceOperatorStateRow) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO source_operator_state (
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                  is_active = excluded.is_active,
                  strategy_state = excluded.strategy_state,
                  current_strategy_id = excluded.current_strategy_id,
                  latest_strategy_id = excluded.latest_strategy_id,
                  last_onboarding_run_id = excluded.last_onboarding_run_id,
                  last_collection_status = excluded.last_collection_status,
                  last_collection_started_at = excluded.last_collection_started_at,
                  last_collection_finished_at = excluded.last_collection_finished_at,
                  last_collection_error = excluded.last_collection_error,
                  activated_at = excluded.activated_at,
                  deactivated_at = excluded.deactivated_at,
                  updated_at = excluded.updated_at
                """,
                (
                    row["source_id"],
                    row["is_active"],
                    row["strategy_state"],
                    row["current_strategy_id"],
                    row["latest_strategy_id"],
                    row["last_onboarding_run_id"],
                    row["last_collection_status"],
                    row["last_collection_started_at"],
                    row["last_collection_finished_at"],
                    row["last_collection_error"],
                    row["activated_at"],
                    row["deactivated_at"],
                    row["updated_at"],
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def insert_strategy_version(self, row: SourceStrategyVersionRow) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO source_strategy_versions (
                  strategy_id,
                  source_id,
                  version,
                  strategy_status,
                  entrypoint_url,
                  fetch_via,
                  content_mode,
                  parser_profile,
                  max_items_per_run,
                  strategy_summary_json,
                  strategy_details_json,
                  created_from_run_id,
                  created_at,
                  approved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["strategy_id"],
                    row["source_id"],
                    row["version"],
                    row["strategy_status"],
                    row["entrypoint_url"],
                    row["fetch_via"],
                    row["content_mode"],
                    row["parser_profile"],
                    row["max_items_per_run"],
                    row["strategy_summary_json"],
                    row["strategy_details_json"],
                    row["created_from_run_id"],
                    row["created_at"],
                    row["approved_at"],
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def list_strategy_versions(self, source_id: str) -> list[SourceStrategyVersionRow]:
        return self.list_strategy_versions_by_source_ids([source_id]).get(source_id, [])

    def list_strategy_versions_by_source_ids(
        self,
        source_ids: list[str],
    ) -> dict[str, list[SourceStrategyVersionRow]]:
        if not source_ids:
            return {}
        connection = self._connect()
        try:
            placeholders = ", ".join("?" for _ in source_ids)
            rows = connection.execute(
                f"""
                SELECT
                  strategy_id,
                  source_id,
                  version,
                  strategy_status,
                  entrypoint_url,
                  fetch_via,
                  content_mode,
                  parser_profile,
                  max_items_per_run,
                  strategy_summary_json,
                  strategy_details_json,
                  created_from_run_id,
                  created_at,
                  approved_at
                FROM source_strategy_versions
                WHERE source_id IN ({placeholders})
                ORDER BY source_id ASC, version DESC, created_at DESC
                """,
                tuple(source_ids),
            ).fetchall()
        finally:
            connection.close()
        grouped: dict[str, list[SourceStrategyVersionRow]] = {source_id: [] for source_id in source_ids}
        for row in rows:
            strategy = _row_to_strategy_version(row)
            grouped[strategy["source_id"]].append(strategy)
        return grouped

    def insert_onboarding_run(self, row: SourceOnboardingRunRow) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO source_onboarding_runs (
                  onboarding_run_id,
                  source_id,
                  status,
                  worker_kind,
                  worker_ref,
                  submitted_at,
                  started_at,
                  finished_at,
                  proposed_strategy_id,
                  error_message,
                  result_summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["onboarding_run_id"],
                    row["source_id"],
                    row["status"],
                    row["worker_kind"],
                    row["worker_ref"],
                    row["submitted_at"],
                    row["started_at"],
                    row["finished_at"],
                    row["proposed_strategy_id"],
                    row["error_message"],
                    row["result_summary_json"],
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def update_onboarding_run(
        self,
        onboarding_run_id: str,
        *,
        status: SourceOnboardingRunStatus,
        proposed_strategy_id: str | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
        error_message: str | None = None,
        result_summary_json: str | None = None,
    ) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                UPDATE source_onboarding_runs
                SET
                  status = ?,
                  proposed_strategy_id = ?,
                  started_at = COALESCE(?, started_at),
                  finished_at = COALESCE(?, finished_at),
                  error_message = ?,
                  result_summary_json = ?
                WHERE onboarding_run_id = ?
                """,
                (
                    status,
                    proposed_strategy_id,
                    started_at,
                    finished_at,
                    error_message,
                    result_summary_json,
                    onboarding_run_id,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def list_onboarding_runs(self, source_id: str) -> list[SourceOnboardingRunRow]:
        return self.list_onboarding_runs_by_source_ids([source_id]).get(source_id, [])

    def list_onboarding_runs_by_source_ids(
        self,
        source_ids: list[str],
    ) -> dict[str, list[SourceOnboardingRunRow]]:
        if not source_ids:
            return {}
        connection = self._connect()
        try:
            placeholders = ", ".join("?" for _ in source_ids)
            rows = connection.execute(
                f"""
                SELECT
                  onboarding_run_id,
                  source_id,
                  status,
                  worker_kind,
                  worker_ref,
                  submitted_at,
                  started_at,
                  finished_at,
                  proposed_strategy_id,
                  error_message,
                  result_summary_json
                FROM source_onboarding_runs
                WHERE source_id IN ({placeholders})
                ORDER BY source_id ASC, submitted_at DESC, onboarding_run_id DESC
                """,
                tuple(source_ids),
            ).fetchall()
        finally:
            connection.close()
        grouped: dict[str, list[SourceOnboardingRunRow]] = {source_id: [] for source_id in source_ids}
        for row in rows:
            run = _row_to_onboarding_run(row)
            grouped[run["source_id"]].append(run)
        return grouped


def _row_to_operator_state(row: sqlite3.Row) -> SourceOperatorStateRow:
    return SourceOperatorStateRow(
        source_id=str(row["source_id"]),
        is_active=int(row["is_active"]),
        strategy_state=SourceStrategyState(str(row["strategy_state"])),
        current_strategy_id=None
        if row["current_strategy_id"] is None
        else str(row["current_strategy_id"]),
        latest_strategy_id=None if row["latest_strategy_id"] is None else str(row["latest_strategy_id"]),
        last_onboarding_run_id=None
        if row["last_onboarding_run_id"] is None
        else str(row["last_onboarding_run_id"]),
        last_collection_status=SourceCollectionStatus(str(row["last_collection_status"])),
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


def _row_to_strategy_version(row: sqlite3.Row) -> SourceStrategyVersionRow:
    return SourceStrategyVersionRow(
        strategy_id=str(row["strategy_id"]),
        source_id=str(row["source_id"]),
        version=int(row["version"]),
        strategy_status=SourceStrategyStatus(str(row["strategy_status"])),
        entrypoint_url=str(row["entrypoint_url"]),
        fetch_via=SourceFetchVia(str(row["fetch_via"])),
        content_mode=SourceContentMode(str(row["content_mode"])),
        parser_profile=None if row["parser_profile"] is None else str(row["parser_profile"]),
        max_items_per_run=int(row["max_items_per_run"]),
        strategy_summary_json=str(row["strategy_summary_json"]),
        strategy_details_json=str(row["strategy_details_json"]),
        created_from_run_id=None
        if row["created_from_run_id"] is None
        else str(row["created_from_run_id"]),
        created_at=str(row["created_at"]),
        approved_at=None if row["approved_at"] is None else str(row["approved_at"]),
    )


def _row_to_onboarding_run(row: sqlite3.Row) -> SourceOnboardingRunRow:
    return SourceOnboardingRunRow(
        onboarding_run_id=str(row["onboarding_run_id"]),
        source_id=str(row["source_id"]),
        status=SourceOnboardingRunStatus(str(row["status"])),
        worker_kind=str(row["worker_kind"]),
        worker_ref=None if row["worker_ref"] is None else str(row["worker_ref"]),
        submitted_at=str(row["submitted_at"]),
        started_at=None if row["started_at"] is None else str(row["started_at"]),
        finished_at=None if row["finished_at"] is None else str(row["finished_at"]),
        proposed_strategy_id=None
        if row["proposed_strategy_id"] is None
        else str(row["proposed_strategy_id"]),
        error_message=None if row["error_message"] is None else str(row["error_message"]),
        result_summary_json=None
        if row["result_summary_json"] is None
        else str(row["result_summary_json"]),
    )


def _initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    source_strategy_state_values = _sql_enum_values(SOURCE_STRATEGY_STATE_VALUES)
    source_collection_status_values = _sql_enum_values(SOURCE_COLLECTION_STATUS_VALUES)
    source_strategy_status_values = _sql_enum_values(SOURCE_STRATEGY_STATUS_VALUES)
    source_onboarding_run_status_values = _sql_enum_values(SOURCE_ONBOARDING_RUN_STATUS_VALUES)
    statements = (
        f"""
        CREATE TABLE IF NOT EXISTS source_operator_state (
          source_id TEXT PRIMARY KEY,
          is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0,1)),
          strategy_state TEXT NOT NULL DEFAULT '{SourceStrategyState.MISSING.value}'
            CHECK (strategy_state IN ({source_strategy_state_values})),
          current_strategy_id TEXT,
          latest_strategy_id TEXT,
          last_onboarding_run_id TEXT,
          last_collection_status TEXT NOT NULL DEFAULT '{SourceCollectionStatus.IDLE.value}'
            CHECK (last_collection_status IN ({source_collection_status_values})),
          last_collection_started_at TEXT,
          last_collection_finished_at TEXT,
          last_collection_error TEXT,
          activated_at TEXT,
          deactivated_at TEXT,
          updated_at TEXT NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS source_strategy_versions (
          strategy_id TEXT PRIMARY KEY,
          source_id TEXT NOT NULL,
          version INTEGER NOT NULL,
          strategy_status TEXT NOT NULL
            CHECK (strategy_status IN ({source_strategy_status_values})),
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
        f"""
        CREATE TABLE IF NOT EXISTS source_onboarding_runs (
          onboarding_run_id TEXT PRIMARY KEY,
          source_id TEXT NOT NULL,
          status TEXT NOT NULL
            CHECK (status IN ({source_onboarding_run_status_values})),
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


def _sql_enum_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)
