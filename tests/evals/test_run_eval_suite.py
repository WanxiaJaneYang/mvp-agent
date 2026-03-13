import unittest
from pathlib import Path

from evals import run_eval_suite


class EvalRunnerTests(unittest.TestCase):
    def test_retrieval_case_passes_when_expected_order_and_size_match(self):
        case = {
            "type": "retrieval",
            "query_text": "inflation",
            "pack_size": 2,
            "fts_rows": [
                {
                    "chunk_id": "chunk_001",
                    "doc_id": "doc_001",
                    "text": "inflation inflation",
                    "source_id": "src_a",
                    "publisher": "Federal Reserve",
                    "published_at": "2026-03-10T10:00:00Z",
                    "credibility_tier": 1,
                },
                {
                    "chunk_id": "chunk_002",
                    "doc_id": "doc_002",
                    "text": "inflation",
                    "source_id": "src_b",
                    "publisher": "Reuters",
                    "published_at": "2026-03-09T10:00:00Z",
                    "credibility_tier": 2,
                },
            ],
            "expected": {
                "chunk_ids": ["chunk_001", "chunk_002"],
                "pack_size": 2,
            },
        }

        errors = run_eval_suite._run_retrieval_case(case)

        self.assertEqual(errors, [])

    def test_postprocess_case_passes_when_abstain_output_matches(self):
        case = {
            "type": "postprocess",
            "validation_result": {
                "status": "retry",
                "synthesis": {
                    "prevailing": [
                        {
                            "text": "[Insufficient evidence to support this claim]",
                            "citation_ids": [],
                        }
                    ]
                },
                "report": {"removed_bullets": 4},
                "validation_attempts": 2,
                "max_validation_attempts": 2,
                "retry_exhausted": True,
            },
            "expected": {
                "status": "abstained",
                "abstain_reason": "validation_retry_exhausted",
            },
        }

        errors = run_eval_suite._run_postprocess_case(case)

        self.assertEqual(errors, [])

    def test_unknown_case_type_is_reported_by_main_dispatch(self):
        case = {
            "id": "BAD-001",
            "type": "unknown",
            "expected": {},
        }

        failure = run_eval_suite._run_case(case)

        self.assertEqual(failure, ["BAD-001: unknown case type: unknown"])

    def test_run_case_reports_runtime_exception_as_failure(self):
        case = {
            "id": "RET-ERR",
            "type": "retrieval",
            "query_text": "inflation",
            "pack_size": 1,
            "fts_rows": [
                {
                    "chunk_id": "chunk_001",
                    "doc_id": "doc_001",
                    "text": "inflation",
                    "source_id": "src_a",
                    "publisher": "Federal Reserve",
                    "published_at": "2026-03-10T10:00:00Z",
                    "credibility_tier": 9,
                }
            ],
            "expected": {"chunk_ids": ["chunk_001"], "pack_size": 1},
        }

        failure = run_eval_suite._run_case(case)

        self.assertEqual(len(failure), 1)
        self.assertIn("RET-ERR: exception:", failure[0])

    def test_golden_cases_include_retrieval_and_postprocess_types(self):
        golden_dir = Path(run_eval_suite.ROOT / "evals" / "golden")

        cases = run_eval_suite._load_cases(golden_dir)
        case_types = {case["type"] for case in cases}

        self.assertIn("retrieval", case_types)
        self.assertIn("postprocess", case_types)

    def test_readme_documents_supported_case_types_and_future_todo(self):
        readme_text = (run_eval_suite.ROOT / "evals" / "README.md").read_text(encoding="utf-8")

        self.assertIn("retrieval", readme_text)
        self.assertIn("postprocess", readme_text)
        self.assertIn("TODO", readme_text)
        self.assertIn("retrieval -> validation -> abstain", readme_text)

    def test_literature_review_case_fails_on_unexpected_extra_reason_codes(self):
        case = {
            "type": "literature_review",
            "synthesis": {
                "brief": {
                    "bottom_line": "Macro cooling is widening the market-policy gap.",
                    "top_takeaways": ["Cooling macro data matters."],
                },
                "issues": [
                    {
                        "issue_id": "issue_001",
                        "issue_question": "Will cooling growth change Fed expectations?",
                        "prevailing": [
                            {
                                "text": "Reuters says traders are turning more dovish.",
                                "novelty_vs_prior_brief": "strengthened",
                                "why_it_matters": "",
                            }
                        ],
                        "counter": [],
                        "minority": [],
                        "watch": [],
                    }
                ],
            },
            "expected": {
                "passes": False,
                "reason_codes": ["pseudo_analysis"],
            },
        }

        errors = run_eval_suite._run_literature_review_case(case)

        self.assertTrue(
            any(
                "expected reason_codes=['pseudo_analysis'], got" in error
                for error in errors
            )
        )

    def test_literature_review_reason_codes_continue_after_duplicate_issue(self):
        synthesis = {
            "brief": {
                "bottom_line": "Macro cooling is widening the market-policy gap.",
                "top_takeaways": ["Cooling macro data matters."],
            },
            "issues": [
                {
                    "issue_id": "issue_001",
                    "issue_question": "Will cooling growth change Fed expectations?",
                    "prevailing": [
                        {
                            "text": "Cooling growth is shifting rate expectations.",
                            "novelty_vs_prior_brief": "strengthened",
                            "why_it_matters": "Rates can reprice quickly.",
                        }
                    ],
                    "counter": [],
                    "minority": [],
                    "watch": [],
                },
                {
                    "issue_id": "issue_002",
                    "issue_question": "Will cooling growth change Fed expectations?",
                    "prevailing": [
                        {
                            "text": "Reuters says the same cooling-growth story is spreading.",
                            "novelty_vs_prior_brief": "unknown",
                            "why_it_matters": "",
                        }
                    ],
                    "counter": [],
                    "minority": [],
                    "watch": [],
                },
            ],
        }

        reason_codes = run_eval_suite._literature_review_reason_codes(synthesis)

        self.assertIn("duplicate_issue", reason_codes)
        self.assertIn("empty_why_it_matters", reason_codes)
        self.assertIn("unsupported_novelty", reason_codes)
        self.assertIn("pseudo_analysis", reason_codes)

    def test_literature_review_reason_codes_reject_invalid_novelty_labels(self):
        synthesis = {
            "brief": {
                "bottom_line": "Macro cooling is widening the market-policy gap.",
                "top_takeaways": ["Cooling macro data matters."],
            },
            "issues": [
                {
                    "issue_id": "issue_001",
                    "issue_question": "Will cooling growth change Fed expectations?",
                    "prevailing": [
                        {
                            "text": "Cooling growth is shifting rate expectations.",
                            "novelty_vs_prior_brief": "stale",
                            "why_it_matters": "Rates can reprice quickly.",
                        }
                    ],
                    "counter": [],
                    "minority": [],
                    "watch": [],
                }
            ],
        }

        reason_codes = run_eval_suite._literature_review_reason_codes(synthesis)

        self.assertIn("unsupported_novelty", reason_codes)


if __name__ == "__main__":
    unittest.main()
