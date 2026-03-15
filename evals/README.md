# Evals

`run_eval_suite.py` executes deterministic golden eval cases for current runtime contracts.

## Run

```bash
python evals/run_eval_suite.py
```

The same golden eval suite now runs in GitHub Actions CI on pull requests to `master`.

Mandatory daily-brief quality gates:

```bash
python -m unittest discover -s tests/evals -p "test_*.py" -v
python -m unittest tests.agent.daily_brief.test_runner tests.agent.delivery.test_html_report tests.agent.synthesis.test_postprocess tests.agent.validators.test_citation_validator tests.agent.daily_brief.test_editorial_planner tests.agent.daily_brief.test_issue_retrieval -v
```

## Golden Case Files

- Path: `evals/golden/case*.json`
- Minimum required: 10
- Supported types:
  - `daily_brief_stage`: validates fixture-backed daily-brief stage demos and regression slices
    - persisted `corpus_summary.json`, `brief_plan.json`, `issue_evidence_scopes.json`, `issue_map.json`, `claim_objects.json`, `synthesis.json`, and final HTML
    - abstain render closure without leaking validator placeholders
    - fixture/live publish-gate parity against the same payload set
  - `citation`: validates stage-8 citation behavior (`ok`/`partial`/`retry`)
  - `retrieval`: validates evidence-pack ordering and pack-size enforcement
  - `postprocess`: validates abstain shaping for failed validation outcomes
  - `literature_review`: validates whether a rendered brief still satisfies the analyst-brief contract
    - duplicate issue detection
    - missing `why_it_matters`
    - unsupported/empty novelty labels
    - pseudo-analysis / source-by-source paraphrase
    - missing top summary (`Bottom line` / `Key takeaways`)

## TODO

- Expand chained `retrieval -> validation -> abstain` daily-brief stage cases beyond the current baseline, abstain, and parity slices.
- Expand literature-review cases with issue-budget compression and unsupported-delta examples.
