import sqlite3
import tempfile
import unittest
from pathlib import Path

from apps.agent.portfolio.input_store import (
    PortfolioPosition,
    load_portfolio_positions,
    replace_portfolio_positions,
)
from apps.agent.storage.sqlite_runtime import runtime_db_path


class PortfolioInputStoreTests(unittest.TestCase):
    def test_replace_and_load_positions_persist_local_holdings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            replace_portfolio_positions(
                base_dir=base_dir,
                positions=[
                    PortfolioPosition(
                        ticker="spy",
                        weight_pct=60.0,
                        asset_type="etf",
                        notes="us equities, large cap",
                    ),
                    PortfolioPosition(
                        ticker="tlt",
                        weight_pct=40.0,
                        asset_type="bond",
                        notes="treasury, duration",
                    ),
                ],
                recorded_at_utc="2026-03-10T16:00:00Z",
            )

            loaded = load_portfolio_positions(base_dir=base_dir)
            connection = sqlite3.connect(runtime_db_path(base_dir=base_dir))
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

        self.assertEqual(
            loaded,
            [
                PortfolioPosition(
                    ticker="SPY",
                    weight_pct=60.0,
                    asset_type="etf",
                    notes="us equities, large cap",
                ),
                PortfolioPosition(
                    ticker="TLT",
                    weight_pct=40.0,
                    asset_type="bond",
                    notes="treasury, duration",
                ),
            ],
        )
        self.assertEqual(
            rows,
            [
                ("SPY", 60.0, "etf", "us equities, large cap"),
                ("TLT", 40.0, "bond", "treasury, duration"),
            ],
        )

    def test_replace_portfolio_positions_rejects_duplicate_tickers_after_normalization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                replace_portfolio_positions(
                    base_dir=Path(tmpdir),
                    positions=[
                        PortfolioPosition(ticker="spy", weight_pct=50.0),
                        PortfolioPosition(ticker="SPY", weight_pct=25.0),
                    ],
                    recorded_at_utc="2026-03-10T16:00:00Z",
                )


if __name__ == "__main__":
    unittest.main()
