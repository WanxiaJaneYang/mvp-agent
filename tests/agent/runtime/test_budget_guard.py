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

    def test_blocks_when_hourly_cap_is_reached_exactly(self):
        caps = BudgetCaps(monthly_usd=100.0, daily_usd=3.0, hourly_usd=0.10)
        decision = evaluate_budget_guard(
            hourly_spend_usd=0.09,
            daily_spend_usd=1.0,
            monthly_spend_usd=20.0,
            next_estimated_cost_usd=0.01,
            caps=caps,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("hourly", decision.exceeded_windows)

    def test_blocks_when_daily_cap_is_reached_exactly(self):
        caps = BudgetCaps(monthly_usd=100.0, daily_usd=3.0, hourly_usd=0.10)
        decision = evaluate_budget_guard(
            hourly_spend_usd=0.01,
            daily_spend_usd=2.99,
            monthly_spend_usd=20.0,
            next_estimated_cost_usd=0.01,
            caps=caps,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("daily", decision.exceeded_windows)

    def test_blocks_when_monthly_cap_is_reached_exactly(self):
        caps = BudgetCaps(monthly_usd=100.0, daily_usd=3.0, hourly_usd=0.10)
        decision = evaluate_budget_guard(
            hourly_spend_usd=0.01,
            daily_spend_usd=1.0,
            monthly_spend_usd=99.99,
            next_estimated_cost_usd=0.01,
            caps=caps,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("monthly", decision.exceeded_windows)

    def test_blocks_when_multiple_caps_would_be_exceeded(self):
        caps = BudgetCaps(monthly_usd=100.0, daily_usd=3.0, hourly_usd=0.10)
        decision = evaluate_budget_guard(
            hourly_spend_usd=0.095,
            daily_spend_usd=2.99,
            monthly_spend_usd=20.0,
            next_estimated_cost_usd=0.02,
            caps=caps,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("hourly", decision.exceeded_windows)
        self.assertIn("daily", decision.exceeded_windows)

    def test_negative_next_estimated_cost_treated_as_zero(self):
        caps = BudgetCaps(monthly_usd=100.0, daily_usd=3.0, hourly_usd=0.10)
        decision = evaluate_budget_guard(
            hourly_spend_usd=0.05,
            daily_spend_usd=1.5,
            monthly_spend_usd=30.0,
            next_estimated_cost_usd=-1.0,
            caps=caps,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.exceeded_windows, [])

    def test_negative_spend_values_raise_error(self):
        caps = BudgetCaps()
        with self.assertRaises(ValueError):
            evaluate_budget_guard(
                hourly_spend_usd=-0.01,
                daily_spend_usd=0.0,
                monthly_spend_usd=0.0,
                next_estimated_cost_usd=0.0,
                caps=caps,
            )

    def test_non_positive_caps_raise_error(self):
        with self.assertRaises(ValueError):
            evaluate_budget_guard(
                hourly_spend_usd=0.0,
                daily_spend_usd=0.0,
                monthly_spend_usd=0.0,
                next_estimated_cost_usd=0.0,
                caps=BudgetCaps(hourly_usd=0.0, daily_usd=3.0, monthly_usd=100.0),
            )

    def test_uses_unrounded_values_for_blocking_decision(self):
        caps = BudgetCaps(hourly_usd=0.10, daily_usd=3.0, monthly_usd=100.0)
        decision = evaluate_budget_guard(
            hourly_spend_usd=0.094,
            daily_spend_usd=1.0,
            monthly_spend_usd=20.0,
            next_estimated_cost_usd=0.005,
            caps=caps,
        )
        # Raw projected hourly spend is 0.099 (< 0.10), so this should not hard-stop.
        self.assertTrue(decision.allowed)


if __name__ == "__main__":
    unittest.main()
