import unittest

from apps.agent.runtime.budget_guard import BudgetDecision
from apps.agent.runtime.cost_ledger import BudgetWindowSnapshot, build_budget_ledger_rows


class CostLedgerTests(unittest.TestCase):
    def test_builds_budget_ledger_rows_for_all_windows(self):
        rows = build_budget_ledger_rows(
            run_id="run_ledger_1",
            recorded_at="2026-03-10T08:00:00Z",
            decision=BudgetDecision(
                allowed=True,
                exceeded_windows=[],
                reason=None,
                projected_spend={"hourly": 0.04, "daily": 0.80, "monthly": 12.50},
                caps={"hourly": 0.10, "daily": 3.0, "monthly": 100.0},
            ),
            windows={
                "hourly": BudgetWindowSnapshot(
                    window_start="2026-03-10T08:00:00Z",
                    window_end="2026-03-10T08:59:59Z",
                    cost_usd=0.04,
                ),
                "daily": BudgetWindowSnapshot(
                    window_start="2026-03-10T00:00:00Z",
                    window_end="2026-03-10T23:59:59Z",
                    cost_usd=0.80,
                ),
                "monthly": BudgetWindowSnapshot(
                    window_start="2026-03-01T00:00:00Z",
                    window_end="2026-03-31T23:59:59Z",
                    cost_usd=12.50,
                ),
            },
        )

        self.assertEqual(len(rows), 3)
        self.assertEqual([row["window_type"] for row in rows], ["hourly", "daily", "monthly"])
        self.assertEqual(rows[0]["run_id"], "run_ledger_1")
        self.assertEqual(rows[0]["cap_usd"], 0.10)
        self.assertEqual(rows[1]["cap_usd"], 3.0)
        self.assertEqual(rows[2]["cap_usd"], 100.0)
        self.assertEqual([row["exceeded"] for row in rows], [0, 0, 0])

    def test_marks_exceeded_windows_in_ledger_rows(self):
        rows = build_budget_ledger_rows(
            run_id="run_ledger_2",
            recorded_at="2026-03-10T09:00:00Z",
            decision=BudgetDecision(
                allowed=False,
                exceeded_windows=["hourly", "daily"],
                reason="Budget hard-stop triggered",
                projected_spend={"hourly": 0.10, "daily": 3.00, "monthly": 12.50},
                caps={"hourly": 0.10, "daily": 3.0, "monthly": 100.0},
            ),
            windows={
                "hourly": BudgetWindowSnapshot(
                    window_start="2026-03-10T09:00:00Z",
                    window_end="2026-03-10T09:59:59Z",
                    cost_usd=0.10,
                ),
                "daily": BudgetWindowSnapshot(
                    window_start="2026-03-10T00:00:00Z",
                    window_end="2026-03-10T23:59:59Z",
                    cost_usd=3.00,
                ),
                "monthly": BudgetWindowSnapshot(
                    window_start="2026-03-01T00:00:00Z",
                    window_end="2026-03-31T23:59:59Z",
                    cost_usd=12.50,
                ),
            },
        )

        self.assertEqual([row["exceeded"] for row in rows], [1, 1, 0])


if __name__ == "__main__":
    unittest.main()
