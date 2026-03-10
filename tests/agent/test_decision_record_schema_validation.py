import subprocess
import sys
import unittest
from pathlib import Path

from scripts.validate_decision_record_schema import validate_decision_record, validate_example_file


class DecisionRecordSchemaValidationTests(unittest.TestCase):
    def test_script_entrypoint_passes(self):
        repo_root = Path(__file__).resolve().parents[2]
        script_path = repo_root / "scripts" / "validate_decision_record_schema.py"

        completed = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Decision record schema validation passed.", completed.stdout)

    def test_valid_example_passes(self):
        errors = validate_example_file()
        self.assertEqual(errors, [])

    def test_pipeline_fixture_passes(self):
        errors = validate_example_file(
            Path("artifacts/modelling/examples/decision_record_pipeline_fixture.json")
        )
        self.assertEqual(errors, [])

    def test_supported_claim_requires_citation(self):
        record = {
            "schema_version": "decision_record.v1",
            "record_id": "dr_1",
            "run_id": "run_1",
            "run_type": "daily_brief",
            "generated_at_utc": "2026-02-19T12:35:00Z",
            "status": "ok",
            "claims": [
                {
                    "claim_id": "c1",
                    "section": "prevailing",
                    "text": "Claim",
                    "citation_ids": [],
                    "coverage_status": "supported",
                }
            ],
            "rejected_alternatives": [],
            "risk_flags": [],
            "budget_snapshot": {
                "hourly_spend_usd": 0.01,
                "hourly_cap_usd": 0.1,
                "daily_spend_usd": 0.01,
                "daily_cap_usd": 3.0,
                "monthly_spend_usd": 0.01,
                "monthly_cap_usd": 100.0,
                "allowed": True,
            },
            "guardrail_checks": {
                "citation_check": "pass",
                "paywall_check": "pass",
                "diversity_check": "pass",
                "budget_check": "pass",
                "notes": [],
            },
            "artifacts": {
                "synthesis_id": "syn_1",
                "output_path": "artifacts/daily/2026-02-19/brief.html",
                "output_sha256": "a" * 64,
            },
            "decision_rationale": {
                "summary": "ok",
                "confidence_label": "high",
                "key_drivers": [],
                "uncertainties": [],
            },
        }

        errors = validate_decision_record(record)
        self.assertTrue(any("supported claim" in error for error in errors))

    def test_budget_allowed_false_when_cap_reached(self):
        record = {
            "schema_version": "decision_record.v1",
            "record_id": "dr_1",
            "run_id": "run_1",
            "run_type": "daily_brief",
            "generated_at_utc": "2026-02-19T12:35:00Z",
            "status": "ok",
            "claims": [],
            "rejected_alternatives": [],
            "risk_flags": [],
            "budget_snapshot": {
                "hourly_spend_usd": 0.1,
                "hourly_cap_usd": 0.1,
                "daily_spend_usd": 0.01,
                "daily_cap_usd": 3.0,
                "monthly_spend_usd": 0.01,
                "monthly_cap_usd": 100.0,
                "allowed": True,
            },
            "guardrail_checks": {
                "citation_check": "pass",
                "paywall_check": "pass",
                "diversity_check": "pass",
                "budget_check": "pass",
                "notes": [],
            },
            "artifacts": {
                "synthesis_id": "syn_1",
                "output_path": "artifacts/daily/2026-02-19/brief.html",
                "output_sha256": "a" * 64,
            },
            "decision_rationale": {
                "summary": "ok",
                "confidence_label": "high",
                "key_drivers": [],
                "uncertainties": [],
            },
        }

        errors = validate_decision_record(record)
        self.assertTrue(any("budget_snapshot.allowed" in error for error in errors))

    def test_missing_required_claim_fields_fail(self):
        record = {
            "schema_version": "decision_record.v1",
            "record_id": "dr_1",
            "run_id": "run_1",
            "run_type": "daily_brief",
            "generated_at_utc": "2026-02-19T12:35:00Z",
            "status": "ok",
            "claims": [
                {
                    "section": "prevailing",
                    "citation_ids": ["c1"],
                    "coverage_status": "supported",
                }
            ],
            "rejected_alternatives": [],
            "risk_flags": [],
            "budget_snapshot": {
                "hourly_spend_usd": 0.01,
                "hourly_cap_usd": 0.1,
                "daily_spend_usd": 0.01,
                "daily_cap_usd": 3.0,
                "monthly_spend_usd": 0.01,
                "monthly_cap_usd": 100.0,
                "allowed": True,
            },
            "guardrail_checks": {
                "citation_check": "pass",
                "paywall_check": "pass",
                "diversity_check": "pass",
                "budget_check": "pass",
                "notes": [],
            },
            "artifacts": {"output_sha256": "a" * 64},
            "decision_rationale": {
                "summary": "ok",
                "confidence_label": "high",
                "key_drivers": [],
                "uncertainties": [],
            },
        }

        errors = validate_decision_record(record)
        self.assertTrue(any("claim_id" in error for error in errors))
        self.assertTrue(any("text" in error for error in errors))

    def test_missing_required_rationale_and_rejected_fields_fail(self):
        record = {
            "schema_version": "decision_record.v1",
            "record_id": "dr_1",
            "run_id": "run_1",
            "run_type": "daily_brief",
            "generated_at_utc": "2026-02-19T12:35:00Z",
            "status": "ok",
            "claims": [],
            "rejected_alternatives": [{"notes": "x"}],
            "risk_flags": [],
            "budget_snapshot": {
                "hourly_spend_usd": 0.01,
                "hourly_cap_usd": 0.1,
                "daily_spend_usd": 0.01,
                "daily_cap_usd": 3.0,
                "monthly_spend_usd": 0.01,
                "monthly_cap_usd": 100.0,
                "allowed": True,
            },
            "guardrail_checks": {
                "citation_check": "pass",
                "paywall_check": "pass",
                "diversity_check": "pass",
                "budget_check": "pass",
                "notes": [],
            },
            "artifacts": {"output_sha256": "a" * 64},
            "decision_rationale": {
                "confidence_label": "high",
                "uncertainties": [],
            },
        }

        errors = validate_decision_record(record)
        self.assertTrue(any("decision_rationale.summary" in error for error in errors))
        self.assertTrue(any("decision_rationale.key_drivers" in error for error in errors))
        self.assertTrue(any("rejected_alternatives[].candidate_summary" in error for error in errors))
        self.assertTrue(any("rejected_alternatives[].reason_code" in error for error in errors))

    def test_rejected_alternative_reason_code_must_be_allowed_enum(self):
        record = {
            "schema_version": "decision_record.v1",
            "record_id": "dr_1",
            "run_id": "run_1",
            "run_type": "daily_brief",
            "generated_at_utc": "2026-02-19T12:35:00Z",
            "status": "ok",
            "claims": [],
            "rejected_alternatives": [
                {
                    "candidate_summary": "X",
                    "reason_code": "not_allowed",
                }
            ],
            "risk_flags": [],
            "budget_snapshot": {
                "hourly_spend_usd": 0.01,
                "hourly_cap_usd": 0.1,
                "daily_spend_usd": 0.01,
                "daily_cap_usd": 3.0,
                "monthly_spend_usd": 0.01,
                "monthly_cap_usd": 100.0,
                "allowed": True,
            },
            "guardrail_checks": {
                "citation_check": "pass",
                "paywall_check": "pass",
                "diversity_check": "pass",
                "budget_check": "pass",
                "notes": [],
            },
            "artifacts": {"output_sha256": "a" * 64},
            "decision_rationale": {
                "summary": "ok",
                "confidence_label": "high",
                "key_drivers": [],
                "uncertainties": [],
            },
        }

        errors = validate_decision_record(record)
        self.assertTrue(any("reason_code must be one of" in error for error in errors))

    def test_artifact_fields_enforce_types_and_sha256_shape(self):
        record = {
            "schema_version": "decision_record.v1",
            "record_id": "dr_1",
            "run_id": "run_1",
            "run_type": "daily_brief",
            "generated_at_utc": "2026-02-19T12:35:00Z",
            "status": "ok",
            "claims": [],
            "rejected_alternatives": [],
            "risk_flags": [],
            "budget_snapshot": {
                "hourly_spend_usd": 0.01,
                "hourly_cap_usd": 0.1,
                "daily_spend_usd": 0.01,
                "daily_cap_usd": 3.0,
                "monthly_spend_usd": 0.01,
                "monthly_cap_usd": 100.0,
                "allowed": True,
            },
            "guardrail_checks": {
                "citation_check": "pass",
                "paywall_check": "pass",
                "diversity_check": "pass",
                "budget_check": "pass",
                "notes": [],
            },
            "artifacts": {
                "synthesis_id": 123,
                "output_path": 456,
                "output_sha256": "short",
            },
            "decision_rationale": {
                "summary": "ok",
                "confidence_label": "high",
                "key_drivers": [],
                "uncertainties": [],
            },
        }

        errors = validate_decision_record(record)
        self.assertTrue(any("artifacts.synthesis_id" in error for error in errors))
        self.assertTrue(any("artifacts.output_path" in error for error in errors))
        self.assertTrue(any("artifacts.output_sha256" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
