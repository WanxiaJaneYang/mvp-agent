import unittest

from apps.agent.daily_brief.critic import review_brief_locally


class DailyBriefCriticTests(unittest.TestCase):
    def test_flags_source_by_source_paraphrase_claims(self) -> None:
        report = review_brief_locally(
            synthesis={
                "issues": [
                    {
                        "issue_id": "issue_growth",
                        "issue_question": "Will softer growth change near-term Fed expectations?",
                        "summary": "The debate is split.",
                        "prevailing": [
                            {
                                "claim_id": "claim_prevailing",
                                "text": "Reuters says growth is slowing.",
                                "citation_ids": ["cite_001"],
                                "confidence_label": "medium",
                            }
                        ],
                        "counter": [
                            {
                                "claim_id": "claim_counter",
                                "text": "Federal Reserve says policy is steady.",
                                "citation_ids": ["cite_002"],
                                "confidence_label": "medium",
                            }
                        ],
                        "minority": [],
                        "watch": [],
                    }
                ]
            },
            citation_store={
                "cite_001": {"publisher": "Reuters", "title": "Growth slows", "published_at": "2026-03-12T08:00:00Z"},
                "cite_002": {
                    "publisher": "Federal Reserve",
                    "title": "Policy remains steady",
                    "published_at": "2026-03-12T09:00:00Z",
                },
            },
        )

        self.assertEqual(report["status"], "warn")
        self.assertIn("source_by_source_paraphrase", report["reason_codes"])
        self.assertEqual(
            report["flagged_claim_ids"],
            ["claim_counter", "claim_prevailing"],
        )

    def test_flags_thesis_mismatch_and_empty_why_it_matters(self) -> None:
        report = review_brief_locally(
            synthesis={
                "issues": [
                    {
                        "issue_id": "issue_oil",
                        "issue_question": "Will oil prices keep rising over the next few weeks?",
                        "summary": "The issue is oil direction.",
                        "prevailing": [
                            {
                                "claim_id": "claim_prevailing",
                                "text": "Supply risks keep the near-term oil view constructive.",
                                "citation_ids": ["cite_001"],
                                "confidence_label": "high",
                                "why_it_matters": "Energy inflation could stay elevated.",
                            }
                        ],
                        "counter": [
                            {
                                "claim_id": "claim_counter",
                                "text": "Payroll growth moderated in the latest jobs report.",
                                "citation_ids": ["cite_002"],
                                "confidence_label": "medium",
                                "why_it_matters": "   ",
                            }
                        ],
                        "minority": [],
                        "watch": [],
                    }
                ]
            },
            citation_store={
                "cite_001": {
                    "publisher": "Reuters",
                    "title": "Oil rises on supply risks",
                    "published_at": "2026-03-12T08:00:00Z",
                },
                "cite_002": {
                    "publisher": "BLS",
                    "title": "Payroll growth moderates",
                    "published_at": "2026-03-12T08:30:00Z",
                },
            },
        )

        self.assertEqual(report["status"], "fail")
        self.assertIn("thesis_mismatch", report["reason_codes"])
        self.assertIn("empty_why_it_matters", report["reason_codes"])
        self.assertEqual(report["flagged_claim_ids"], ["claim_counter"])

    def test_passes_clean_issue_centered_claims_without_rewriting(self) -> None:
        synthesis = {
            "issues": [
                {
                    "issue_id": "issue_rates",
                    "issue_question": "Will softer growth change near-term Fed expectations?",
                    "summary": "The issue is whether softer growth changes the policy path.",
                    "prevailing": [
                        {
                            "claim_id": "claim_prevailing",
                            "text": (
                                "Softer growth is raising later-cut expectations without "
                                "forcing an immediate pivot."
                            ),
                            "citation_ids": ["cite_001"],
                            "confidence_label": "medium",
                            "why_it_matters": "Rate-sensitive assets remain exposed to data surprises.",
                        }
                    ],
                    "counter": [
                        {
                            "claim_id": "claim_counter",
                            "text": "Sticky inflation still argues against a quick pivot even if growth cools.",
                            "citation_ids": ["cite_002"],
                            "confidence_label": "medium",
                            "why_it_matters": "Policy can stay restrictive longer than growth bulls expect.",
                        }
                    ],
                    "minority": [
                        {
                            "claim_id": "claim_minority",
                            "text": "A smaller camp expects growth weakness to force faster easing later this year.",
                            "citation_ids": ["cite_003"],
                            "confidence_label": "low",
                            "why_it_matters": "Downside macro tail risk is still present.",
                        }
                    ],
                    "watch": [
                        {
                            "claim_id": "claim_watch",
                            "text": "The next CPI release is the main falsification point for the whole debate.",
                            "citation_ids": ["cite_004"],
                            "confidence_label": "high",
                            "why_it_matters": "One inflation print can reprice the issue quickly.",
                        }
                    ],
                }
            ]
        }

        report = review_brief_locally(
            synthesis=synthesis,
            citation_store={
                "cite_001": {
                    "publisher": "Reuters",
                    "title": "Growth slows",
                    "published_at": "2026-03-12T08:00:00Z",
                },
                "cite_002": {
                    "publisher": "Federal Reserve",
                    "title": "Policy steady",
                    "published_at": "2026-03-12T09:00:00Z",
                },
                "cite_003": {
                    "publisher": "WSJ",
                    "title": "Sharper slowdown view",
                    "published_at": "2026-03-12T10:00:00Z",
                },
                "cite_004": {
                    "publisher": "BLS",
                    "title": "CPI release schedule",
                    "published_at": "2026-03-12T11:00:00Z",
                },
            },
        )

        self.assertEqual(report, {"status": "pass", "reason_codes": [], "flagged_claim_ids": []})
        self.assertEqual(
            synthesis["issues"][0]["prevailing"][0]["text"],
            "Softer growth is raising later-cut expectations without forcing an immediate pivot.",
        )


if __name__ == "__main__":
    unittest.main()
