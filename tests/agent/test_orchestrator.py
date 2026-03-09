import unittest

from apps.agent.orchestrator import run_pipeline
from apps.agent.pipeline.types import RunType


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

    def test_rejects_unknown_run_type(self):
        with self.assertRaises(ValueError):
            run_pipeline(
                run_id="run_bad",
                run_type="not_a_real_run_type",
                stages=[],
                recorder=lambda snapshot: None,
            )

    def test_accepts_run_type_enum(self):
        result = run_pipeline(
            run_id="run_enum",
            run_type=RunType.DAILY_BRIEF,
            stages=[],
            recorder=lambda snapshot: None,
        )

        self.assertEqual(result["run_type"], "daily_brief")


if __name__ == "__main__":
    unittest.main()
