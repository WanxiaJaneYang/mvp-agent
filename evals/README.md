# Evals

`run_eval_suite.py` executes golden modelling cases for citation validation and runtime budget guard behavior.

## Run

```bash
python evals/run_eval_suite.py
```

## Golden Case Files

- Path: `evals/golden/case*.json`
- Minimum required: 10
- Types:
  - `citation`: validates stage-8 citation behavior (`ok`/`partial`/`retry`)
  - `budget`: validates budget hard-stop decisions
