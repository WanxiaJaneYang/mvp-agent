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

## TODO

- Add chained `retrieval -> validation -> abstain` golden cases once the first integrated path is ready.
