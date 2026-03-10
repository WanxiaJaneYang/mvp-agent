# Database Guidelines

> Current persistence rules for a modelling-first repository.

---

## Current State

The authoritative database contract currently lives in:
- `artifacts/modelling/data_model.md`

There is **no full runtime persistence layer checked in yet**. Treat schema work as modelling-first until concrete storage code is introduced.

---

## Rules

- If a change affects persistence shape, update `artifacts/modelling/data_model.md`.
- Keep fixtures and validators aligned with the planned schema.
- Do not add ad-hoc SQLite files, migrations, or local persistence helpers without also updating modelling docs and tests.

---

## Examples

- Planned run and ledger fields are documented in `artifacts/modelling/data_model.md`
- Decision-record examples are validated via `scripts/validate_decision_record_schema.py`
- Artifact structure is validated via `scripts/validate_artifacts.py`

---

## Anti-Patterns

- Do not treat runtime code as the only source of truth for persistence contracts.
- Do not land schema-shape changes without updating modelling artifacts.
- Do not invent migration workflow docs until an actual migration tool exists in the repo.
