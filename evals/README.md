# Evals

`run_eval_suite.py` executes golden citation-validation cases.

## Run

```bash
python evals/run_eval_suite.py
```

## Golden Case Files

- Path: `evals/golden/case*.json`
- Minimum required: 10
- Type:
  - `citation`: validates stage-8 citation behavior (`ok`/`partial`/`retry`)
