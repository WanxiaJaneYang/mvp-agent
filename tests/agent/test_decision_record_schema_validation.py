import unittest
from pathlib import Path

from scripts.validate_decision_record_schema import validate_decision_record, validate_example_file


class DecisionRecordSchemaValidationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
