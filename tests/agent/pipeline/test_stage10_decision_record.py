import json
import tempfile
import unittest
from pathlib import Path

from apps.agent.pipeline.decision_record_validation import validate_decision_record
from apps.agent.pipeline.stage10_decision_record import build_and_persist_decision_record


class Stage10DecisionRecordTests(unittest.TestCase):
    def test_issue_centered_synthesis_preserves_issue_context_in_claims(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "daily" / "2026-02-19" / "brief.html"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("<html>brief</html>", encoding="utf-8")

            result = build_and_persist_decision_record(
                base_dir=Path(tmpdir),
                run_id="run_issue_shape",
                run_type="daily_brief",
                stage8_status="ok",
                synthesis={
                    "issues": [
                        {
                            "issue_id": "issue_001",
                            "issue_question": "Will oil prices keep rising?",
                            "title": "Will oil prices keep rising?",
                            "summary": "Supply and demand evidence point in different directions.",
                            "prevailing": [
                                {
                                    "claim_id": "claim_001",
                                    "claim_kind": "prevailing",
                                    "text": "Supply risks support near-term upside.",
                                    "citation_ids": ["c1"],
                                    "why_it_matters": "Energy inflation can stay sticky.",
                                    "novelty_vs_prior_brief": "strengthened",
                                }
                            ],
                            "counter": [
                                {
                                    "claim_id": "claim_002",
                                    "claim_kind": "counter",
                                    "text": "Demand softness could steady prices soon.",
                                    "citation_ids": ["c2"],
                                    "why_it_matters": "The rally can stall quickly.",
                                    "novelty_vs_prior_brief": "continued",
                                }
                            ],
                            "minority": [],
                            "watch": [],
                        }
                    ]
                },
                removed_bullets=0,
                budget_snapshot={
                    "hourly_spend_usd": 0.03,
                    "hourly_cap_usd": 0.10,
                    "daily_spend_usd": 0.8,
                    "daily_cap_usd": 3.0,
                    "monthly_spend_usd": 12.4,
                    "monthly_cap_usd": 100.0,
                    "allowed": True,
                },
                guardrail_checks={
                    "citation_check": "pass",
                    "paywall_check": "pass",
                    "diversity_check": "pass",
                    "budget_check": "pass",
                    "notes": [],
                },
                output_path=output_path,
                generated_at_utc="2026-02-19T08:00:00Z",
            )

            claims = result["decision_record"]["claims"]
            self.assertEqual([claim["section"] for claim in claims], ["prevailing", "counter"])
            self.assertEqual(claims[0]["issue_id"], "issue_001")
            self.assertEqual(claims[0]["issue_title"], "Will oil prices keep rising?")
            self.assertEqual(claims[0]["claim_id"], "claim_001")
            self.assertEqual(claims[0]["claim_kind"], "prevailing")
            self.assertEqual(claims[0]["citation_ids"], ["c1"])
            self.assertEqual(claims[0]["why_it_matters"], "Energy inflation can stay sticky.")
            self.assertEqual(claims[0]["novelty_vs_prior_brief"], "strengthened")
            self.assertEqual(validate_decision_record(result["decision_record"]), [])

    def test_decision_record_validator_rejects_invalid_editorial_claim_fields(self):
        record = {
            "schema_version": "decision_record.v1",
            "record_id": "record_bad_fields",
            "run_id": "run_bad_fields",
            "run_type": "daily_brief",
            "generated_at_utc": "2026-02-19T08:00:00Z",
            "status": "ok",
            "claims": [
                {
                    "claim_id": "claim_001",
                    "section": "prevailing",
                    "text": "Claim text.",
                    "citation_ids": ["c1"],
                    "coverage_status": "supported",
                    "claim_kind": "invalid_kind",
                    "why_it_matters": None,
                    "novelty_vs_prior_brief": "stale",
                }
            ],
            "budget_snapshot": {
                "hourly_spend_usd": 0.03,
                "hourly_cap_usd": 0.10,
                "daily_spend_usd": 0.8,
                "daily_cap_usd": 3.0,
                "monthly_spend_usd": 12.4,
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
                "output_path": "brief.html",
                "output_sha256": "0" * 64,
                "synthesis_id": "syn_run_bad_fields",
            },
            "decision_rationale": {
                "summary": "Summary",
                "confidence_label": "medium",
                "key_drivers": ["driver"],
                "uncertainties": [],
            },
            "rejected_alternatives": [],
            "risk_flags": [],
        }

        errors = validate_decision_record(record)

        self.assertIn("claim claim_kind must be prevailing|counter|minority|watch|changed", errors)
        self.assertIn("claim why_it_matters must be a string", errors)
        self.assertIn(
            "claim novelty_vs_prior_brief must be new|continued|reframed|weakened|strengthened|reversed|unknown",
            errors,
        )
    def test_persists_decision_record_to_date_partitioned_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "daily" / "2026-02-19" / "brief.html"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("<html>brief</html>", encoding="utf-8")

            result = build_and_persist_decision_record(
                base_dir=Path(tmpdir),
                run_id="run_123",
                run_type="daily_brief",
                stage8_status="partial",
                synthesis={
                    "prevailing": [
                        {
                            "text": "Claim",
                            "citation_ids": ["c1"],
                        }
                    ]
                },
                removed_bullets=1,
                budget_snapshot={
                    "hourly_spend_usd": 0.03,
                    "hourly_cap_usd": 0.10,
                    "daily_spend_usd": 0.8,
                    "daily_cap_usd": 3.0,
                    "monthly_spend_usd": 12.4,
                    "monthly_cap_usd": 100.0,
                    "allowed": True,
                },
                guardrail_checks={
                    "citation_check": "warn",
                    "paywall_check": "pass",
                    "diversity_check": "pass",
                    "budget_check": "pass",
                    "notes": ["1 uncited claim downgraded"],
                },
                output_path=output_path,
                generated_at_utc="2026-02-19T08:00:00Z",
            )

            record_path = Path(result["record_path"])
            self.assertTrue(record_path.exists())
            self.assertIn("decision_records", str(record_path))
            expected = (
                Path(tmpdir) / "artifacts" / "decision_records" / "2026-02-19" / "run_123.json"
            )
            self.assertEqual(record_path, expected)

            persisted = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["schema_version"], "decision_record.v1")
            self.assertEqual(persisted["run_id"], "run_123")
            self.assertEqual(persisted["run_type"], "daily_brief")
            self.assertEqual(persisted["status"], "partial")
            self.assertEqual(persisted["artifacts"]["output_path"], str(output_path))
            self.assertTrue(persisted["artifacts"]["output_sha256"])
            self.assertEqual(validate_decision_record(persisted), [])

    def test_missing_output_artifact_downgrades_to_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_and_persist_decision_record(
                base_dir=Path(tmpdir),
                run_id="run_missing_output",
                run_type="daily_brief",
                stage8_status="ok",
                synthesis={"prevailing": [{"text": "Claim", "citation_ids": ["c1"]}]},
                removed_bullets=0,
                budget_snapshot={
                    "hourly_spend_usd": 0.03,
                    "hourly_cap_usd": 0.10,
                    "daily_spend_usd": 0.8,
                    "daily_cap_usd": 3.0,
                    "monthly_spend_usd": 12.4,
                    "monthly_cap_usd": 100.0,
                    "allowed": True,
                },
                guardrail_checks={
                    "citation_check": "pass",
                    "paywall_check": "pass",
                    "diversity_check": "pass",
                    "budget_check": "pass",
                    "notes": [],
                },
                output_path=None,
            )

            persisted = result["decision_record"]
            self.assertEqual(persisted["status"], "failed")
            self.assertEqual(validate_decision_record(persisted), [])

    def test_counterarguments_section_is_normalized_to_counter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "daily" / "2026-02-19" / "brief.html"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("<html>brief</html>", encoding="utf-8")

            result = build_and_persist_decision_record(
                base_dir=Path(tmpdir),
                run_id="run_section_norm",
                run_type="daily_brief",
                stage8_status="ok",
                synthesis={"counterarguments": [{"text": "Counter claim", "citation_ids": ["c2"]}]},
                removed_bullets=0,
                budget_snapshot={
                    "hourly_spend_usd": 0.03,
                    "hourly_cap_usd": 0.10,
                    "daily_spend_usd": 0.8,
                    "daily_cap_usd": 3.0,
                    "monthly_spend_usd": 12.4,
                    "monthly_cap_usd": 100.0,
                    "allowed": True,
                },
                guardrail_checks={
                    "citation_check": "pass",
                    "paywall_check": "pass",
                    "diversity_check": "pass",
                    "budget_check": "pass",
                    "notes": [],
                },
                output_path=output_path,
            )

            sections = [claim["section"] for claim in result["decision_record"]["claims"]]
            self.assertIn("counter", sections)
            self.assertNotIn("counterarguments", sections)
            self.assertEqual(validate_decision_record(result["decision_record"]), [])

    def test_non_schema_sections_are_filtered_out(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "daily" / "2026-02-19" / "brief.html"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("<html>brief</html>", encoding="utf-8")

            result = build_and_persist_decision_record(
                base_dir=Path(tmpdir),
                run_id="run_filter_sections",
                run_type="daily_brief",
                stage8_status="ok",
                synthesis={"metadata": [{"text": "Meta note", "citation_ids": ["c9"]}]},
                removed_bullets=0,
                budget_snapshot={
                    "hourly_spend_usd": 0.03,
                    "hourly_cap_usd": 0.10,
                    "daily_spend_usd": 0.8,
                    "daily_cap_usd": 3.0,
                    "monthly_spend_usd": 12.4,
                    "monthly_cap_usd": 100.0,
                    "allowed": True,
                },
                guardrail_checks={
                    "citation_check": "pass",
                    "paywall_check": "pass",
                    "diversity_check": "pass",
                    "budget_check": "pass",
                    "notes": [],
                },
                output_path=output_path,
            )

            sections = [claim["section"] for claim in result["decision_record"]["claims"]]
            self.assertEqual(sections, [])
            self.assertEqual(validate_decision_record(result["decision_record"]), [])


if __name__ == "__main__":
    unittest.main()
