import unittest

from apps.agent.synthesis.postprocess import build_abstain_synthesis, finalize_validation_outcome


class SynthesisPostprocessTests(unittest.TestCase):
    def test_builds_explicit_abstain_bullets_for_each_core_section(self):
        synthesis = build_abstain_synthesis(
            reason="citation validation failed after retry budget was exhausted"
        )

        self.assertEqual(
            synthesis,
            {
                "prevailing": [
                    {
                        "text": "[Insufficient evidence to produce a validated output]",
                        "citation_ids": [],
                        "confidence_label": "abstained",
                    }
                ],
                "counter": [
                    {
                        "text": "[Insufficient evidence to produce a validated output]",
                        "citation_ids": [],
                        "confidence_label": "abstained",
                    }
                ],
                "minority": [
                    {
                        "text": "[Insufficient evidence to produce a validated output]",
                        "citation_ids": [],
                        "confidence_label": "abstained",
                    }
                ],
                "watch": [
                    {
                        "text": "[Insufficient evidence to produce a validated output]",
                        "citation_ids": [],
                        "confidence_label": "abstained",
                    }
                ],
                "meta": {
                    "status": "abstained",
                    "reason": "citation validation failed after retry budget was exhausted",
                },
            },
        )

    def test_finalize_validation_outcome_passes_ok_through_unchanged(self):
        validation_result = {
            "status": "ok",
            "synthesis": {"prevailing": [{"text": "Validated claim", "citation_ids": ["c1"]}]},
            "report": {"removed_bullets": 0},
        }

        result = finalize_validation_outcome(validation_result=validation_result)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["synthesis"], validation_result["synthesis"])
        self.assertIsNone(result["abstain_reason"])

    def test_finalize_validation_outcome_preserves_partial_synthesis(self):
        validation_result = {
            "status": "partial",
            "synthesis": {
                "prevailing": [
                    {"text": "[Insufficient evidence to support this claim]", "citation_ids": []}
                ]
            },
            "report": {"removed_bullets": 1},
        }

        result = finalize_validation_outcome(validation_result=validation_result)

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["synthesis"], validation_result["synthesis"])
        self.assertIsNone(result["abstain_reason"])

    def test_finalize_validation_outcome_requires_retry_exhaustion_before_abstaining(self):
        validation_result = {
            "status": "retry",
            "synthesis": {
                "prevailing": [
                    {"text": "[Insufficient evidence to support this claim]", "citation_ids": []}
                ]
            },
            "report": {
                "removed_bullets": 4,
                "empty_core_sections": ["prevailing", "counter"],
            },
            "validation_attempts": 1,
            "max_validation_attempts": 2,
            "retry_exhausted": False,
        }

        with self.assertRaises(ValueError):
            finalize_validation_outcome(validation_result=validation_result)

    def test_finalize_validation_outcome_maps_exhausted_retry_to_abstained_output(self):
        validation_result = {
            "status": "retry",
            "synthesis": {
                "prevailing": [
                    {"text": "[Insufficient evidence to support this claim]", "citation_ids": []}
                ]
            },
            "report": {
                "removed_bullets": 4,
                "empty_core_sections": ["prevailing", "counter"],
            },
            "validation_attempts": 2,
            "max_validation_attempts": 2,
            "retry_exhausted": True,
        }

        result = finalize_validation_outcome(validation_result=validation_result)

        self.assertEqual(result["status"], "abstained")
        self.assertEqual(result["abstain_reason"], "validation_retry_exhausted")
        self.assertEqual(
            result["synthesis"]["meta"]["reason"],
            "validation_retry_exhausted",
        )


if __name__ == "__main__":
    unittest.main()
