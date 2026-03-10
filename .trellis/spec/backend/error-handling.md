# Error Handling

> How errors are handled in the current Python codebase.

---

## Rules

- Raise `ValueError` for invalid caller inputs or impossible local configuration.
- Return typed status objects for expected pipeline outcomes.
- Add file/path context when surfacing validation failures from scripts.

---

## Patterns

### Raise for invalid inputs

Examples:
- `apps/agent/runtime/budget_guard.py`
- `apps/agent/orchestrator.py`

Use exceptions when the caller passed invalid state and execution should stop immediately.

### Return status for expected runtime outcomes

Examples:
- `apps/agent/pipeline/types.py`
- `apps/agent/orchestrator.py`

Use `RunStatus` or `StageResult` when failure/partial/budget-stop is part of the normal contract.

### Preserve context in scripts

Example:
- `scripts/validate_artifacts.py`

When wrapping parse/file errors, include the file path in the raised error.

---

## Anti-Patterns

- Do not swallow errors and keep running silently.
- Do not use exceptions for expected stage statuses that already have typed result objects.
- Do not raise generic errors without enough context to identify the failing file or field.
