import unittest

from apps.agent.synthesis.postprocess import build_abstain_synthesis


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


if __name__ == "__main__":
    unittest.main()
