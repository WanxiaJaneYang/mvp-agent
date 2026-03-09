import unittest

from apps.agent.orchestrator import run_pipeline


class OrchestratorTests(unittest.TestCase):
    def test_records_running_and_ok_lifecycle(self):
        lifecycle_events = []

        def recorder(snapshot):
            lifecycle_events.append(snapshot)

        def stage(context):
            return {"status": "ok"}

        result = run_pipeline(
            run_id="run_123",
            run_type="daily_brief",
            stages=[stage],
            recorder=recorder,
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(lifecycle_events), 2)
        self.assertEqual(lifecycle_events[0]["status"], "running")
        self.assertEqual(lifecycle_events[1]["status"], "ok")
        self.assertEqual(lifecycle_events[0]["run_type"], "daily_brief")
        self.assertEqual(lifecycle_events[1]["run_type"], "daily_brief")


if __name__ == "__main__":
    unittest.main()
