import unittest

from apps.agent.delivery.scheduler import (
    DailyBriefSchedule,
    compute_next_scheduled_run,
    scheduled_local_date,
)


class DailyBriefSchedulerTests(unittest.TestCase):
    def test_compute_next_scheduled_run_keeps_same_local_day_before_cutoff(self):
        result = compute_next_scheduled_run(
            now_utc="2026-03-10T22:30:00Z",
            schedule=DailyBriefSchedule(timezone_name="Asia/Singapore", delivery_hour=7, delivery_minute=5),
        )

        self.assertEqual(result, "2026-03-10T23:05:00Z")

    def test_compute_next_scheduled_run_rolls_forward_after_cutoff(self):
        result = compute_next_scheduled_run(
            now_utc="2026-03-11T00:30:00Z",
            schedule=DailyBriefSchedule(timezone_name="Asia/Singapore", delivery_hour=7, delivery_minute=5),
        )

        self.assertEqual(result, "2026-03-11T23:05:00Z")

    def test_scheduled_local_date_uses_user_timezone(self):
        result = scheduled_local_date(
            generated_at_utc="2026-03-10T23:30:00Z",
            schedule=DailyBriefSchedule(timezone_name="Asia/Singapore", delivery_hour=7, delivery_minute=5),
        )

        self.assertEqual(result, "2026-03-11")


if __name__ == "__main__":
    unittest.main()
