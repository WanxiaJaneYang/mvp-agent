import unittest

from apps.agent.runtime.budget_guard import BudgetCaps, evaluate_budget_guard


class BudgetGuardTests(unittest.TestCase):
    def test_allows_when_under_all_caps(self):
        caps = BudgetCaps(monthly_usd=100.0, daily_usd=3.0, hourly_usd=0.10)
        decision = evaluate_budget_guard(
            hourly_spend_usd=0.02,
            daily_spend_usd=1.0,
            monthly_spend_usd=20.0,
            next_estimated_cost_usd=0.01,
            caps=caps,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.exceeded_windows, [])

    def test_blocks_when_hourly_cap_would_be_exceeded(self):
        caps = BudgetCaps(monthly_usd=100.0, daily_usd=3.0, hourly_usd=0.10)
        decision = evaluate_budget_guard(
            hourly_spend_usd=0.095,
            daily_spend_usd=1.0,
            monthly_spend_usd=20.0,
            next_estimated_cost_usd=0.01,
            caps=caps,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("hourly", decision.exceeded_windows)

    def test_blocks_when_daily_cap_already_exceeded(self):
        caps = BudgetCaps(monthly_usd=100.0, daily_usd=3.0, hourly_usd=0.10)
        decision = evaluate_budget_guard(
            hourly_spend_usd=0.02,
            daily_spend_usd=3.01,
            monthly_spend_usd=20.0,
            next_estimated_cost_usd=0.0,
            caps=caps,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("daily", decision.exceeded_windows)

    def test_default_caps_match_project_constraints(self):
        decision = evaluate_budget_guard(
            hourly_spend_usd=0.0,
            daily_spend_usd=0.0,
            monthly_spend_usd=0.0,
            next_estimated_cost_usd=0.0,
        )
        self.assertEqual(decision.caps["hourly"], 0.10)
        self.assertEqual(decision.caps["daily"], 3.0)
        self.assertEqual(decision.caps["monthly"], 100.0)


if __name__ == "__main__":
    unittest.main()
