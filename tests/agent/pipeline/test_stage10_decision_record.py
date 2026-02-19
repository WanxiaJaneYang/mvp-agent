import json
import tempfile
import unittest
from pathlib import Path

from apps.agent.pipeline.stage10_decision_record import build_and_persist_decision_record
from scripts.validate_decision_record_schema import validate_decision_record


class Stage10DecisionRecordTests(unittest.TestCase):
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
            )

            record_path = Path(result["record_path"])
            self.assertTrue(record_path.exists())
            self.assertIn("decision_records", str(record_path))
            self.assertTrue(record_path.name.endswith("run_123.json"))

            persisted = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["schema_version"], "decision_record.v1")
            self.assertEqual(persisted["run_id"], "run_123")
            self.assertEqual(persisted["run_type"], "daily_brief")
            self.assertEqual(persisted["status"], "partial")
            self.assertEqual(persisted["artifacts"]["output_path"], str(output_path))
            self.assertTrue(persisted["artifacts"]["output_sha256"])
            self.assertEqual(validate_decision_record(persisted), [])


if __name__ == "__main__":
    unittest.main()
