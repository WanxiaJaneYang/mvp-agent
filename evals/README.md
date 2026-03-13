# Evals

`run_eval_suite.py` executes deterministic golden eval cases for current runtime contracts.

## Run

```bash
python evals/run_eval_suite.py
```

The same golden eval suite now runs in GitHub Actions CI on pull requests to `master`.

## Golden Case Files

- Path: `evals/golden/case*.json`
- Minimum required: 10
- Supported types:
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

- Add chained `retrieval -> validation -> abstain` golden cases once the first integrated path is ready.
- Expand literature-review cases with issue-budget compression and unsupported-delta examples.
