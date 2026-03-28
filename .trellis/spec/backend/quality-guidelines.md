# Quality Guidelines

> Backend quality standards for the current repo.

---

## Required Verification

Use the repo's full CI validation flow:

```bash
python -m ruff check apps tests scripts tools
python -m mypy apps tools
python scripts/validate_artifacts.py
python scripts/validate_decision_record_schema.py
python -m compileall -q apps tests scripts tools
python evals/run_eval_suite.py
python -m unittest discover -s tests -t . -p "test_*.py" -v
```

Run the relevant subset for small changes and the full suite for cross-cutting changes.

---

## Required Patterns

- Keep modules small and domain-focused.
- Mirror runtime changes with tests under `tests/agent/`.
- Update modelling docs when executable contracts drift.
- Prefer deterministic, offline-friendly unit tests.

---

## Forbidden Patterns

- Do not add network-dependent unit tests.
- Do not land runtime contract changes without test updates.
- Do not introduce new workflow/tooling assumptions copied from JS repos.
- Do not leave Trellis docs/specs behind when the repo conventions changed.

---

## Review Checklist

- Did the change follow existing `apps/agent/` package structure?
- Were types/dataclasses/enums kept consistent?
- Were modelling artifacts updated if schema or payload shape changed?
- Do validators and tests still cover the changed behavior?
