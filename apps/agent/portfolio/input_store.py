from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from apps.agent.pipeline.identifiers import build_prefixed_uuid_id
from apps.agent.storage.sqlite_runtime import ensure_runtime_db, runtime_db_path


@dataclass(frozen=True)
class PortfolioPosition:
    ticker: str
    weight_pct: float
    asset_type: str = "equity"
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def replace_portfolio_positions(
    *,
    base_dir: Path,
    positions: Iterable[PortfolioPosition],
    recorded_at_utc: str,
) -> list[PortfolioPosition]:
    normalized_positions = _normalize_positions(positions=positions)
    ensure_runtime_db(base_dir=base_dir)

    connection = sqlite3.connect(runtime_db_path(base_dir=base_dir))
    try:
        connection.execute("DELETE FROM portfolio_positions")
        connection.executemany(
            """
            INSERT INTO portfolio_positions (
              position_id, ticker, weight_pct, asset_type, notes, created_at, updated_at
            ) VALUES (
              :position_id, :ticker, :weight_pct, :asset_type, :notes, :created_at, :updated_at
            )
            """,
            [
                {
                    "position_id": build_prefixed_uuid_id("position", position.ticker),
                    "ticker": position.ticker,
                    "weight_pct": position.weight_pct,
                    "asset_type": position.asset_type,
                    "notes": position.notes,
                    "created_at": recorded_at_utc,
                    "updated_at": recorded_at_utc,
                }
                for position in normalized_positions
            ],
        )
        connection.commit()
    finally:
        connection.close()

    return normalized_positions


def load_portfolio_positions(*, base_dir: Path) -> list[PortfolioPosition]:
    ensure_runtime_db(base_dir=base_dir)
    connection = sqlite3.connect(runtime_db_path(base_dir=base_dir))
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT ticker, weight_pct, asset_type, notes
            FROM portfolio_positions
            ORDER BY weight_pct DESC, ticker
            """
        ).fetchall()
    finally:
        connection.close()

    return [
        PortfolioPosition(
            ticker=str(row["ticker"]),
            weight_pct=float(row["weight_pct"]),
            asset_type=str(row["asset_type"]),
            notes=None if row["notes"] is None else str(row["notes"]),
        )
        for row in rows
    ]


def _normalize_positions(*, positions: Iterable[PortfolioPosition]) -> list[PortfolioPosition]:
    normalized: list[PortfolioPosition] = []
    seen_tickers: set[str] = set()

    for position in positions:
        ticker = str(position.ticker).strip().upper()
        if not ticker:
            raise ValueError("ticker must be a non-empty string")
        if ticker in seen_tickers:
            raise ValueError(f"duplicate ticker not allowed: {ticker}")
        weight_pct = float(position.weight_pct)
        if weight_pct < 0.0 or weight_pct > 100.0:
            raise ValueError("weight_pct must be between 0 and 100")
        asset_type = str(position.asset_type).strip().lower() or "equity"
        notes = None
        if position.notes is not None:
            stripped_notes = str(position.notes).strip()
            notes = stripped_notes or None

        normalized.append(
            PortfolioPosition(
                ticker=ticker,
                weight_pct=weight_pct,
                asset_type=asset_type,
                notes=notes,
            )
        )
        seen_tickers.add(ticker)

    return normalized
