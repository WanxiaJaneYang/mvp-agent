# Type Safety

> Current typing patterns for the Python backend.

---

## Rules

- Use Python type annotations on public functions and helpers.
- Use `dataclass` for structured internal state.
- Use `Enum` for stable status/run-type vocabularies.
- Use explicit `dict[str, Any]` or `Mapping[str, Any]` at loose payload boundaries.

---

## Preferred Patterns

### Structured internal state

Use dataclasses and enums for lifecycle and stage state.

Examples:
- `apps/agent/pipeline/types.py`
- `apps/agent/runtime/budget_guard.py`

### Boundary payloads

Use `Mapping[str, Any]` for incoming loose data and `dict[str, Any]` for constructed records when the payload is intentionally schema-shaped.

Example:
- `apps/agent/ingest/normalize.py`

### Narrow conversions

Normalize untyped or string inputs at the boundary, then work with typed values internally.

Example:
- `apps/agent/orchestrator.py` normalizes `run_type` into `RunType`

---

## Forbidden Patterns

- Do not introduce untyped public helpers when a small annotation would clarify the contract.
- Do not duplicate magic status strings when an enum already exists.
- Do not return ad-hoc mixed payloads for expected pipeline outcomes when a dataclass already models the state.

---

## Common Mistakes

- Updating enum values in code but not in tests or modelling docs
- Using a free-form dict internally where a dataclass would make required fields obvious
- Adding new payload keys without updating the related tests and fixtures
