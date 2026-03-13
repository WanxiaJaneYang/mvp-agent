# Daily Brief Integrity Issue Mapping

Date: 2026-03-13

## Goal
Translate the checklist in `C:\Users\Lenovo\Downloads\codex_issue_and_tech_fix_checklist.md` into concrete repo issue/doc updates without changing runtime code in this pass.

## Open-Issue Mapping

Keep and extend:
- `#130` for post-scope issue retention after real evidence assignment.
- `#134` for surviving-delivered-claim-only delta semantics.
- `#135` for compressed-mode versus abstain-mode rules.
- `#136` for regression fixtures and eval coverage.
- `#138` for persisted allowlists and final claim delivery state.

Retarget or narrow:
- `#128` from "add a planner" to planner-quality hardening.
- `#129` to explicit end-to-end per-issue evidence binding.
- `#132` to include malformed prose and render-state mismatch.
- `#133` stays a UX issue and should not carry correctness/state-machine fixes.

New local issue draft:
- `issue_139.md` as the umbrella P0 integrity issue for the remaining cross-cutting gap cluster.

Execution plan:
- `docs/plans/2026-03-13-daily-brief-integrity-implementation-plan.md`

Full open-issue order covered there:
- `#135 -> #128 -> #129 -> #130 -> #131 -> #138 -> #134 -> #132 -> #133 -> #136 -> #69 -> #137 -> #74`

## Documentation Surfaces Updated

- `artifacts/PRD.md`
- `artifacts/modelling/citation_contract.md`
- `artifacts/modelling/pipeline.md`
- `artifacts/modelling/data_model.md`
- `artifacts/modelling/decision_record_schema.md`
- `artifacts/modelling/MODELLING_CHECKLIST.md`
- `artifacts/modelling/TODO.md`
- `README.md`

## Contract Corrections Applied

- Brief-level abstain now has an explicit dedicated render mode in the docs.
- Per-issue evidence/citation allowlists are now defined as end-to-end invariants.
- Validator placeholders are documented as internal-only, non-renderable states.
- `What Changed` and visible citations are documented as post-validation derivations from surviving delivered claims only.
- Bottom-line generation is documented as retained-issue synthesis with sanity checks, not token-bundle prose.
