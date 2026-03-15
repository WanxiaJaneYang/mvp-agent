import json
import unittest
from pathlib import Path

from evals import run_eval_suite


class EvalRunnerTests(unittest.TestCase):
    def test_daily_brief_stage_case_passes_when_required_artifacts_and_html_are_present(self):
        case = self._load_golden_case("case20.json")

        failure = run_eval_suite._run_case(case)

        self.assertEqual(failure, [])

    def test_daily_brief_stage_case_reports_missing_artifact_for_declared_expectation(self):
        errors = run_eval_suite._validate_daily_brief_stage_result(
            result={"artifact_dir": str(Path.cwd())},
            expected={"issue_map_count": 1},
        )

        self.assertIn(
            "missing artifact required for issue_map_count expectations: issue_map.json",
            errors,
        )

    def test_daily_brief_stage_case_reports_missing_artifact_dir(self):
        errors = run_eval_suite._validate_daily_brief_stage_result(
            result={"status": "failed"},
            expected={},
        )

        self.assertEqual(errors, ["missing artifact_dir in daily_brief_stage result"])

    def _load_golden_case(self, filename: str) -> dict:
        case_path = run_eval_suite.ROOT / "evals" / "golden" / filename
        return json.loads(case_path.read_text(encoding="utf-8"))

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

        self.assertIn("daily_brief_stage", case_types)
        self.assertIn("retrieval", case_types)
        self.assertIn("postprocess", case_types)

    def test_readme_documents_supported_case_types_and_future_todo(self):
        readme_text = (run_eval_suite.ROOT / "evals" / "README.md").read_text(encoding="utf-8")

        self.assertIn("daily_brief_stage", readme_text)
        self.assertIn("retrieval", readme_text)
        self.assertIn("postprocess", readme_text)
        self.assertIn("TODO", readme_text)
        self.assertIn("retrieval -> validation -> abstain", readme_text)
        self.assertIn('python -m unittest discover -s tests/evals -p "test_*.py" -v', readme_text)
        self.assertIn(
            "python -m unittest tests.agent.daily_brief.test_runner tests.agent.delivery.test_html_report "
            "tests.agent.synthesis.test_postprocess tests.agent.validators.test_citation_validator "
            "tests.agent.daily_brief.test_editorial_planner tests.agent.daily_brief.test_issue_retrieval -v",
            readme_text,
        )

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

    def test_literature_review_reason_codes_include_thesis_mismatch_and_templated_why(self):
        synthesis = {
            "brief": {
                "bottom_line": "The brief drifts off-issue and uses a template implication.",
                "top_takeaways": ["A generic implication is not enough."],
            },
            "issues": [
                {
                    "issue_id": "issue_001",
                    "issue_question": "Will oil prices keep rising over the next few weeks?",
                    "prevailing": [],
                    "counter": [],
                    "minority": [],
                    "watch": [
                        {
                            "text": "Watch payroll growth for signs of labor-market cooling.",
                            "novelty_vs_prior_brief": "continued",
                            "why_it_matters": "Investors should watch this closely.",
                        }
                    ],
                }
            ],
        }

        reason_codes = run_eval_suite._literature_review_reason_codes(synthesis)

        self.assertIn("thesis_mismatch", reason_codes)
        self.assertIn("templated_why_it_matters", reason_codes)

    def test_citation_case_reports_claim_citation_entailment_failure(self):
        case = {
            "type": "citation",
            "synthesis": {
                "prevailing": [
                    {
                        "text": "Oil prices rose after OPEC cut production.",
                        "citation_ids": ["c1"],
                    }
                ],
                "counter": [{"text": "Counter.", "citation_ids": ["c2"]}],
                "minority": [{"text": "Minority.", "citation_ids": ["c3"]}],
                "watch": [{"text": "Watch.", "citation_ids": ["c4"]}],
            },
            "citation_store": {
                "c1": {
                    "id": "c1",
                    "url": "u1",
                    "published_at": "2026-02-19T00:00:00Z",
                    "paywall_policy": "full",
                    "quote_text": "The ECB held rates steady and left guidance unchanged.",
                    "snippet_text": "ECB policymakers emphasized patience on inflation.",
                },
                "c2": {"id": "c2", "url": "u2", "published_at": "2026-02-19T00:00:00Z"},
                "c3": {"id": "c3", "url": "u3", "published_at": "2026-02-19T00:00:00Z"},
                "c4": {"id": "c4", "url": "u4", "published_at": "2026-02-19T00:00:00Z"},
            },
            "expected": {
                "status": "retry",
                "removed_bullets": 1,
            },
        }

        errors = run_eval_suite._run_citation_case(case)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
