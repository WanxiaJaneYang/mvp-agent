# Directory Structure

> How backend code is organized in this project today.

---

## Directory Layout

```text
apps/
  agent/
    ingest/        # fetch/extract/normalize/dedup helpers
    pipeline/      # shared run/stage types and pipeline helpers
    retrieval/     # chunking and retrieval helpers
    runtime/       # budget and cost tracking helpers
    synthesis/     # synthesis post-processing
    validators/    # citation and output validators
    orchestrator.py
tests/
  agent/           # mirrors apps/agent structure
scripts/           # validation entry points used by CI
artifacts/
  modelling/       # planned contracts, schemas, fixtures, backlog
docs/
  adr/             # durable architecture decisions
  plans/           # design and implementation plans
```

---

## Organization Rules

- Add runtime code under the closest `apps/agent/<domain>/` package.
- Add tests under the mirrored `tests/agent/<domain>/` location.
- Put executable verification entry points in `scripts/`.
- Put planned schema/persistence contracts in `artifacts/modelling/`, not inline comments or ad-hoc docs.
- Put durable architecture decisions in `docs/adr/`.
- Keep `docs/plans/` for time-bound design and implementation plans, not long-lived ADRs.

---

## Examples

- `apps/agent/orchestrator.py` pairs with `tests/agent/test_orchestrator.py`
- `apps/agent/runtime/budget_guard.py` pairs with `tests/agent/runtime/test_budget_guard.py`
- `apps/agent/ingest/normalize.py` pairs with `tests/agent/ingest/test_normalize.py`

---

## Anti-Patterns

- Do not introduce a generic `src/` tree; this repo already uses `apps/agent/`.
- Do not place runtime contracts only in `docs/`; mirror them in code and tests.
- Do not add new top-level packages when an existing domain package already fits.
