import unittest

from apps.agent.orchestrator import run_pipeline
from apps.agent.pipeline.types import RunStatus, RunType, StageResult


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

    def test_retries_retryable_stage_until_success(self):
        attempts = {"count": 0}

        def flaky_stage(context):
            attempts["count"] += 1
            if attempts["count"] == 1:
                return StageResult(
                    status=RunStatus.FAILED,
                    error_summary="temporary failure",
                    retryable=True,
                )
            return StageResult(status=RunStatus.OK)

        result = run_pipeline(
            run_id="run_retry_success",
            run_type=RunType.DAILY_BRIEF,
            stages=[flaky_stage],
            recorder=lambda snapshot: None,
            max_stage_attempts=2,
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(attempts["count"], 2)

    def test_fails_when_retry_limit_is_exhausted(self):
        attempts = {"count": 0}

        def always_fails(context):
            attempts["count"] += 1
            return StageResult(
                status=RunStatus.FAILED,
                error_summary="still failing",
                retryable=True,
            )

        result = run_pipeline(
            run_id="run_retry_fail",
            run_type=RunType.DAILY_BRIEF,
            stages=[always_fails],
            recorder=lambda snapshot: None,
            max_stage_attempts=2,
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_summary"], "still failing")
        self.assertEqual(attempts["count"], 2)

    def test_budget_stop_sets_stopped_budget_status(self):
        attempts = {"next_stage_calls": 0}

        def budget_stop_stage(context):
            return StageResult(
                status=RunStatus.STOPPED_BUDGET,
                error_summary="budget hard-stop triggered",
            )

        def should_not_run(context):
            attempts["next_stage_calls"] += 1
            return StageResult(status=RunStatus.OK)

        result = run_pipeline(
            run_id="run_budget_stop",
            run_type=RunType.DAILY_BRIEF,
            stages=[budget_stop_stage, should_not_run],
            recorder=lambda snapshot: None,
        )

        self.assertEqual(result["status"], "stopped_budget")
        self.assertEqual(result["error_summary"], "budget hard-stop triggered")
        self.assertEqual(attempts["next_stage_calls"], 0)

    def test_partial_stage_result_sets_partial_status(self):
        def partial_stage(context):
            return StageResult(
                status=RunStatus.PARTIAL,
                error_summary="one stage completed with degradation",
            )

        def later_ok_stage(context):
            return StageResult(status=RunStatus.OK)

        result = run_pipeline(
            run_id="run_partial",
            run_type=RunType.DAILY_BRIEF,
            stages=[partial_stage, later_ok_stage],
            recorder=lambda snapshot: None,
        )

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["error_summary"], "one stage completed with degradation")


if __name__ == "__main__":
    unittest.main()
