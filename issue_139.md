# [P0][daily-brief-integrity] Close validation/render state gaps, enforce per-issue evidence binding, and harden brief thesis generation

## Status Note (2026-03-14)
The execution program tracked here has now landed on `master` through PRs `#143`-`#157`. Treat this document as historical mapping for the completed stream. Remaining work starts with post-open-issue hygiene and fresh repo/GitHub triage, not by continuing the original execution order below.

## Summary
The current daily-brief pipeline still allows internally inconsistent output. A brief can reach a held or `abstained` state while looking like a normal full brief, placeholder validator text can leak into delivery, `What Changed` can reference claims that did not survive validation, and issue/citation binding is not yet enforced end to end.

## Why This Is P0
- It weakens output trust at the exact point where the system is supposed to withhold or narrow delivery.
- It creates contradictory user-visible states: held brief metadata with publishable-looking issue cards.
- It leaves cross-issue evidence leakage and malformed thesis generation as correctness risks, not just polish gaps.

## Scope
- Add a true brief-level abstain render mode.
- Enforce per-issue evidence/citation allowlists from issue scope through renderer-visible citations.
- Treat validator placeholders as internal-only states.
- Compute `What Changed` and visible citations from surviving delivered claims only.
- Replace token-bundle bottom-line generation with retained-issue thesis synthesis plus sanity checks.

## Acceptance Criteria
1. A final `abstained` brief renders in a dedicated abstain template, not the normal full brief template.
2. Internal validator placeholders never appear in delivered HTML/email.
3. Every rendered claim uses citations from its own issue's allowlisted evidence scope.
4. `What Changed` is computed from surviving validated claims only.
5. The visible citations section is a subset of citations referenced by surviving delivered claims only.
6. Bottom-line generation uses retained issue synthesis and rejects malformed token-stitched prose.
7. Regression tests cover abstain rendering, cross-issue leakage, placeholder suppression, changed-section derivation, citation subset derivation, and thesis safety.

## Related Existing Issues
- Extend `#128` to cover planner-quality hardening rather than only planner introduction.
- Extend `#129` to cover end-to-end per-issue evidence binding.
- Extend `#130` to cover post-scope issue retention after real evidence assignment.
- Extend `#132` to cover malformed prose and render-state mismatch.
- Extend `#134` to define surviving-delivered-claim semantics explicitly.
- Extend `#135` to define compressed-vs-abstain mode and demotion/drop rules clearly.
- Extend `#136` to add regression fixtures/evals for these failures.
- Extend `#138` to persist issue allowlists and final claim delivery state.

## Implementation Streams
- Planner hardening
- Per-issue evidence binding
- Abstain/postprocess/render closure
- Placeholder and surviving-claim semantics
- Critic gate hardening

## Execution Order
1. `#135`
2. `#128`
3. `#129`
4. `#130`
5. `#131`
6. `#138`
7. `#134`
8. `#132`
9. `#133`
10. `#136`
11. `#69`
12. `#137`
13. `#74`

Implementation plan:
- `docs/plans/2026-03-13-daily-brief-integrity-implementation-plan.md`

## Source
- Checklist reviewed from `C:\Users\Lenovo\Downloads\codex_issue_and_tech_fix_checklist.md` on 2026-03-13.
