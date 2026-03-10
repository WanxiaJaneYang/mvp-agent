# Logging Guidelines

> Current logging expectations for this repo.

---

## Current State

This repo does not yet have a shared application logger. The current codebase is intentionally low-noise:
- library code returns values or raises errors
- validation scripts print short pass/fail messages
- tests assert behavior directly instead of inspecting logs

---

## Rules

- Prefer deterministic return values and exceptions over debug prints in library code.
- Keep script output concise and task-oriented.
- Do not log secrets, full paywalled text, or noisy intermediate payload dumps.

---

## Examples

- `scripts/validate_artifacts.py` prints a single success line
- `scripts/validate_decision_record_schema.py` prints explicit validation errors, then exits non-zero
- `apps/agent/*` modules generally avoid logging and stay test-friendly

---

## Anti-Patterns

- Do not add `print()` tracing inside reusable runtime helpers.
- Do not dump full document bodies, secrets, or raw large payloads to stdout.
- Do not introduce a logging framework casually; document it in this spec first if the repo adopts one.
