# Daily Brief Integrity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> Historical note (2026-03-14): this plan was executed and landed on `master` through PRs `#143`-`#157`. Keep it as historical execution mapping only. The next batch starts from repo/GitHub status reconciliation rather than continuing this list as active work.

**Goal:** Cover every currently open GitHub issue in one explicit execution order, while keeping the daily-brief correctness stream ahead of lower-priority retrieval expansion and alert delivery work.

**Architecture:** Treat `#128-#138` as the primary serial daily-brief program because they share planner, retrieval, validator, renderer, and artifact contracts. Keep `#69`, `#137`, and `#74` in the same global order but behind the daily-brief stabilization stream, because they either expand substrate capability or depend on the brief path being trustworthy first.

**Tech Stack:** Python 3.11+, `unittest`, SQLite/FTS5 modelling artifacts, daily-brief runtime under `apps/agent/`, delivery/rendering under `apps/agent/delivery/`

---

## Full Open-Issue Execution Order

Current open issues confirmed on 2026-03-13:
- `#69`
- `#74`
- `#128`
- `#129`
- `#130`
- `#131`
- `#132`
- `#133`
- `#134`
- `#135`
- `#136`
- `#137`
- `#138`

Recommended global order:

1. `#135` `[Product][P1] Define source-scarcity and issue-budget rules in the PRD`
2. `#128` `[P0][architecture] Add a brief-level editorial planner before IssueMap generation`
3. `#129` `[P0][retrieval] Replace single global-query retrieval with corpus-first, issue-aware retrieval`
4. `#130` `[P0][editorial-quality] Add issue deduplication, overlap scoring, and minimum information-gain gating`
5. `#131` `[P0][delivery] Preserve and render why_it_matters and novelty_vs_prior_brief end to end`
6. `#138` `[Data/Observability][P2] Persist IssueMap and StructuredClaim natively in runtime storage`
7. `#134` `[P0][delta] Replace heuristic Changed Since Yesterday with claim-level delta computation`
8. `#132` `[P0][quality-gate] Turn critic into a publish gate and split status labels`
9. `#133` `[Product][P1] Redesign daily brief UX around Bottom line / Key takeaways / Issues / What changed`
10. `#136` `[Quality][P1] Add literature-review evals, not just citation/runtime golden cases`
11. `#69` `P1: Implement true hybrid retrieval on persistent SQLite/FTS5`
12. `#137` `[Tech][P1] Add live HTML/PDF fetching for non-RSS sources`
13. `#74` `P2: Implement alert delivery runtime (M010)`

Why this order:
- `#135` comes first because the rest of the brief stack needs the product contract for compressed mode, abstain mode, issue budget, and demotion/drop behavior.
- `#128` and `#129` define the upstream brief-analysis contract. They must land before downstream validation/render logic can be made correct.
- `#130` depends on actual issue scopes existing, so it follows planner and issue-aware retrieval.
- `#131` should land before storage and delta work so analytical fields survive end to end.
- `#138` should persist the canonical issue/claim state before `#134` and `#132` start depending on it.
- `#134` should stabilize changed-section semantics before publish-gate and hold-state logic in `#132`.
- `#133` is UX polish on top of a stable delivery contract, not a substitute for correctness.
- `#136` locks the final daily-brief behavior in regression fixtures.
- `#69` and `#137` are important, but they are not the shortest path to fixing the current daily-brief integrity failures.
- `#74` remains last because repo guidance already treats alert delivery as downstream of a stable daily-brief path.

Parallelism rule:
- Treat `#128-#138` as one serial stream.
- Do not implement those issues on parallel branches touching the same planner/retrieval/validator/renderer files.
- Only after that stream stabilizes should `#69`, `#137`, and later `#74` branch independently.

### Task 1: Record the full backlog order in repo docs

**Issues:**
- `#69`
- `#74`
- `#128`
- `#129`
- `#130`
- `#131`
- `#132`
- `#133`
- `#134`
- `#135`
- `#136`
- `#137`
- `#138`
- umbrella `#139`

**Files:**
- Modify: `issue_139.md`
- Modify: `docs/plans/2026-03-13-daily-brief-integrity-issue-mapping.md`
- Modify: `artifacts/modelling/TODO.md`
- Modify: `README.md`

**Step 1: Update the issue surfaces**

Add the full global order above into:
- `issue_139.md`
- `docs/plans/2026-03-13-daily-brief-integrity-issue-mapping.md`

**Step 2: Update repo-facing backlog notes**

Make sure the higher-level docs make it clear that:
- daily-brief stabilization leads
- retrieval expansion follows
- alert delivery comes after the brief path is stable

**Step 3: Run doc validation**

Run: `python scripts/validate_artifacts.py`
Expected: PASS

**Step 4: Commit**

```bash
git add issue_139.md docs/plans/2026-03-13-daily-brief-integrity-issue-mapping.md docs/plans/2026-03-13-daily-brief-integrity-implementation-plan.md artifacts/modelling/TODO.md README.md
git commit -m "docs(backlog): record full open-issue execution order"
```

### Task 2: Define compressed-mode and abstain-mode product rules

**Issues:**
- `#135`

**Files:**
- Modify: `artifacts/PRD.md`
- Modify: `artifacts/modelling/citation_contract.md`
- Modify: `artifacts/modelling/pipeline.md`
- Modify: `tests/` only if executable contract tests already exist for docs/scripts

**Step 1: Write the failing contract checks if needed**

If there are doc-validator checks for these surfaces, add or update them so they expect:
- explicit compressed mode
- explicit brief-level abstain mode
- issue demotion/drop behavior
- delivered-claim-only `What Changed`

**Step 2: Run the relevant validators**

Run:
- `python scripts/validate_artifacts.py`
Expected: FAIL if contract surfaces are still incomplete.

**Step 3: Implement the minimal contract updates**

Document:
- source-scarcity rules
- brief-level abstain template rule
- demote/drop instead of padding weak issue 2
- visible citation subset semantics

**Step 4: Re-run validation**

Run:
- `python scripts/validate_artifacts.py`
Expected: PASS

**Step 5: Commit**

```bash
git add artifacts/PRD.md artifacts/modelling/citation_contract.md artifacts/modelling/pipeline.md
git commit -m "docs(product): define compressed and abstain brief rules"
```

### Task 3: Add the brief-level editorial planner and safe bottom-line generation

**Issues:**
- `#128`

**Files:**
- Modify: `apps/agent/daily_brief/editorial_planner.py`
- Modify: `tests/agent/daily_brief/test_editorial_planner.py`
- Check: `docs/plans/2026-03-12-brief-editorial-planner-design.md`

**Step 1: Write the failing tests**

Add tests asserting:
- a `BriefPlan`-style contract exists before `IssueMap`
- bottom line comes from retained issue/thesis artifacts, not token bundles
- malformed thesis strings fall back to a safe template

**Step 2: Run the planner suite**

Run:
- `python -m unittest tests.agent.daily_brief.test_editorial_planner -v`
Expected: FAIL

**Step 3: Implement the minimal planner**

Add:
- brief-level plan object
- safe thesis generation
- internal-only issue seeds

**Step 4: Re-run the planner suite**

Run:
- `python -m unittest tests.agent.daily_brief.test_editorial_planner -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/editorial_planner.py tests/agent/daily_brief/test_editorial_planner.py
git commit -m "feat(daily-brief): add editorial planner and safe thesis generation"
```

### Task 4: Replace global-query retrieval with corpus-first issue-aware retrieval

**Issues:**
- `#129`

**Files:**
- Modify: `apps/agent/daily_brief/issue_retrieval.py`
- Modify: `apps/agent/daily_brief/openai_issue_planner.py`
- Modify: `apps/agent/daily_brief/openai_claim_composer.py`
- Modify: `tests/agent/daily_brief/test_issue_retrieval.py`
- Modify: `tests/agent/daily_brief/test_openai_issue_planner.py`
- Modify: `tests/agent/daily_brief/test_openai_claim_composer.py`

**Step 1: Write the failing tests**

Add tests asserting:
- issue scopes are built from a corpus-first flow
- each issue has its own evidence allowlist
- cross-issue evidence borrowing is rejected

**Step 2: Run the targeted suites**

Run:
- `python -m unittest tests.agent.daily_brief.test_issue_retrieval -v`
- `python -m unittest tests.agent.daily_brief.test_openai_issue_planner -v`
- `python -m unittest tests.agent.daily_brief.test_openai_claim_composer -v`
Expected: FAIL

**Step 3: Implement minimal issue-aware retrieval**

Add:
- corpus-first retrieval inputs
- issue-local evidence scopes
- claim-composer restriction to issue-local evidence/citations

**Step 4: Re-run the targeted suites**

Run the same three commands.
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/issue_retrieval.py apps/agent/daily_brief/openai_issue_planner.py apps/agent/daily_brief/openai_claim_composer.py tests/agent/daily_brief/test_issue_retrieval.py tests/agent/daily_brief/test_openai_issue_planner.py tests/agent/daily_brief/test_openai_claim_composer.py
git commit -m "feat(retrieval): add corpus-first issue-aware retrieval"
```

### Task 5: Add issue overlap scoring and minimum information-gain gating

**Issues:**
- `#130`

**Files:**
- Modify: `apps/agent/daily_brief/editorial_planner.py`
- Modify: `apps/agent/daily_brief/issue_retrieval.py`
- Modify: `tests/agent/daily_brief/test_editorial_planner.py`
- Modify: `tests/agent/daily_brief/test_issue_retrieval.py`

**Step 1: Write the failing tests**

Add tests asserting:
- weak issue 2 is dropped or demoted after evidence assignment
- overlap scoring happens after issue scopes exist
- low-information candidates move to watchlist/takeaways

**Step 2: Run the targeted suites**

Run:
- `python -m unittest tests.agent.daily_brief.test_editorial_planner -v`
- `python -m unittest tests.agent.daily_brief.test_issue_retrieval -v`
Expected: FAIL

**Step 3: Implement minimal gating**

Add deterministic:
- overlap scoring
- information-gain thresholds
- merge/drop/demote behavior

**Step 4: Re-run the targeted suites**

Run the same two commands.
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/editorial_planner.py apps/agent/daily_brief/issue_retrieval.py tests/agent/daily_brief/test_editorial_planner.py tests/agent/daily_brief/test_issue_retrieval.py
git commit -m "feat(editorial): add overlap and information-gain gating"
```

### Task 6: Preserve `why_it_matters` and `novelty_vs_prior_brief` end to end

**Issues:**
- `#131`

**Files:**
- Modify: `apps/agent/daily_brief/synthesis.py`
- Modify: `apps/agent/daily_brief/runner.py`
- Modify: `apps/agent/delivery/html_report.py`
- Modify: `tests/agent/daily_brief/test_synthesis.py`
- Modify: `tests/agent/daily_brief/test_runner.py`
- Modify: `tests/agent/delivery/test_html_report.py`

**Step 1: Write the failing tests**

Add tests asserting:
- analytical claim fields survive synthesis
- those fields survive artifact persistence
- renderer shows them on delivered issue cards

**Step 2: Run the targeted suites**

Run:
- `python -m unittest tests.agent.daily_brief.test_synthesis -v`
- `python -m unittest tests.agent.daily_brief.test_runner -v`
- `python -m unittest tests.agent.delivery.test_html_report -v`
Expected: FAIL

**Step 3: Implement minimal preservation**

Keep `why_it_matters` and `novelty_vs_prior_brief` first-class through synthesis, runner artifacts, and rendering.

**Step 4: Re-run the targeted suites**

Run the same three commands.
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/synthesis.py apps/agent/daily_brief/runner.py apps/agent/delivery/html_report.py tests/agent/daily_brief/test_synthesis.py tests/agent/daily_brief/test_runner.py tests/agent/delivery/test_html_report.py
git commit -m "feat(delivery): preserve why-it-matters and novelty fields"
```

### Task 7: Persist `IssueMap` and `StructuredClaim` natively

**Issues:**
- `#138`

**Files:**
- Modify: `apps/agent/daily_brief/runner.py`
- Modify: `apps/agent/pipeline/types.py`
- Modify: `tests/agent/daily_brief/test_runner.py`
- Modify: `artifacts/modelling/data_model.md`
- Modify: `artifacts/modelling/decision_record_schema.md`

**Step 1: Write the failing tests**

Add tests asserting persisted artifacts include:
- issue allowlists
- structured claims
- delivery status
- validator action
- surviving citation subsets

**Step 2: Run the runner and schema suites**

Run:
- `python -m unittest tests.agent.daily_brief.test_runner -v`
- `python scripts/validate_decision_record_schema.py`
Expected: FAIL

**Step 3: Implement minimal native persistence**

Persist `IssueMap` and `StructuredClaim` state natively in runtime artifacts and keep schema/docs aligned.

**Step 4: Re-run the runner and schema suites**

Run:
- `python -m unittest tests.agent.daily_brief.test_runner -v`
- `python scripts/validate_decision_record_schema.py`
- `python scripts/validate_artifacts.py`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/runner.py apps/agent/pipeline/types.py tests/agent/daily_brief/test_runner.py artifacts/modelling/data_model.md artifacts/modelling/decision_record_schema.md
git commit -m "feat(runtime): persist issue maps and structured claims"
```

### Task 8: Replace heuristic changed-section logic with claim-level delta

**Issues:**
- `#134`

**Files:**
- Modify: `apps/agent/daily_brief/delta.py`
- Modify: `apps/agent/daily_brief/runner.py`
- Modify: `tests/agent/daily_brief/test_runner.py`
- Check: `docs/plans/2026-03-12-claim-delta-and-publish-gate-design.md`

**Step 1: Write the failing tests**

Add tests asserting:
- `What Changed` is derived from claim-level delta objects
- only surviving delivered claims contribute
- downgraded/withheld claims do not reappear in changed output

**Step 2: Run the targeted suite**

Run:
- `python -m unittest tests.agent.daily_brief.test_runner -v`
Expected: FAIL

**Step 3: Implement minimal claim-level delta**

Replace heuristic changed logic with delta-driven derivation from surviving delivered claims only.

**Step 4: Re-run the targeted suite**

Run:
- `python -m unittest tests.agent.daily_brief.test_runner -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/delta.py apps/agent/daily_brief/runner.py tests/agent/daily_brief/test_runner.py
git commit -m "feat(delta): switch changed section to claim-level delta"
```

### Task 9: Turn the critic into a publish gate and close abstain/render-state gaps

**Issues:**
- `#132`

**Files:**
- Modify: `apps/agent/daily_brief/critic.py`
- Modify: `apps/agent/synthesis/postprocess.py`
- Modify: `apps/agent/delivery/html_report.py`
- Modify: `tests/agent/daily_brief/test_critic.py`
- Modify: `tests/agent/synthesis/test_postprocess.py`
- Modify: `tests/agent/delivery/test_html_report.py`

**Step 1: Write the failing tests**

Add tests asserting:
- split `citation_status` and `analytical_status`
- critic can hold publication
- brief-level abstain renders dedicated abstain UI only
- placeholder text does not leak into delivery

**Step 2: Run the targeted suites**

Run:
- `python -m unittest tests.agent.daily_brief.test_critic -v`
- `python -m unittest tests.agent.synthesis.test_postprocess -v`
- `python -m unittest tests.agent.delivery.test_html_report -v`
Expected: FAIL

**Step 3: Implement minimal publish-gate closure**

Add:
- critic reason codes
- split publish statuses
- abstain render-state closure
- placeholder suppression in delivery

**Step 4: Re-run the targeted suites**

Run the same three commands.
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/critic.py apps/agent/synthesis/postprocess.py apps/agent/delivery/html_report.py tests/agent/daily_brief/test_critic.py tests/agent/synthesis/test_postprocess.py tests/agent/delivery/test_html_report.py
git commit -m "feat(quality-gate): add publish gate and abstain closure"
```

### Task 10: Redesign the daily-brief UX on top of the stable delivery contract

**Issues:**
- `#133`

**Files:**
- Modify: `apps/agent/delivery/html_report.py`
- Modify: `tests/agent/delivery/test_html_report.py`

**Step 1: Write the failing UX tests**

Add tests asserting the page is organized around:
- Bottom line
- Key takeaways
- Issues
- What changed

and that those sections consume the already-validated delivery model instead of re-deriving semantics in the renderer.

**Step 2: Run the renderer suite**

Run:
- `python -m unittest tests.agent.delivery.test_html_report -v`
Expected: FAIL

**Step 3: Implement the minimal UX redesign**

Refactor the renderer to present the stabilized issue-centered model in the intended section order.

**Step 4: Re-run the renderer suite**

Run:
- `python -m unittest tests.agent.delivery.test_html_report -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/delivery/html_report.py tests/agent/delivery/test_html_report.py
git commit -m "feat(delivery): redesign daily brief ux"
```

### Task 11: Add literature-review evals and regression coverage

**Issues:**
- `#136`

**Files:**
- Modify: `evals/`
- Modify: `tests/evals/`
- Modify: `tests/agent/daily_brief/test_runner.py`
- Modify: `tests/agent/delivery/test_html_report.py`
- Modify: `tests/agent/validators/test_citation_validator.py`

**Step 1: Add failing eval cases**

Add regression coverage for:
- malformed bottom line
- cross-issue leakage
- abstain render closure
- placeholder suppression
- changed-section surviving-claim semantics
- visible citation subset semantics

**Step 2: Run eval and targeted regression suites**

Run:
- `python -m unittest discover -s tests/evals -p "test_*.py" -v`
- `python -m unittest tests.agent.daily_brief.test_runner tests.agent.delivery.test_html_report tests.agent.validators.test_citation_validator -v`
Expected: FAIL

**Step 3: Implement minimal fixture wiring**

Add the new eval fixtures and expected outputs without reopening settled contracts.

**Step 4: Re-run eval and targeted regression suites**

Run:
- `python -m unittest discover -s tests/evals -p "test_*.py" -v`
- `python -m unittest tests.agent.daily_brief.test_runner tests.agent.delivery.test_html_report tests.agent.validators.test_citation_validator -v`
Expected: PASS

**Step 5: Commit**

```bash
git add evals tests/evals tests/agent/daily_brief/test_runner.py tests/agent/delivery/test_html_report.py tests/agent/validators/test_citation_validator.py
git commit -m "test(daily-brief): add literature-review regressions"
```

### Task 12: Implement true hybrid retrieval on persistent SQLite/FTS5

**Issues:**
- `#69`

**Files:**
- Modify: `apps/agent/` retrieval modules
- Modify: `tests/agent/` retrieval tests
- Modify: `artifacts/modelling/data_model.md` if contracts drift

**Step 1: Write the failing retrieval tests**

Add tests asserting:
- persistent SQLite/FTS5 is part of the supported retrieval path
- lexical and semantic signals both contribute to ranking
- retrieval remains deterministic and bounded

**Step 2: Run the retrieval-focused suite**

Run the relevant retrieval suite for the touched modules.
Expected: FAIL

**Step 3: Implement minimal hybrid retrieval**

Add the smallest persistent hybrid retrieval slice that satisfies the issue without reopening the settled daily-brief delivery contract.

**Step 4: Re-run the retrieval-focused suite**

Run the same retrieval suite plus:
- `python scripts/validate_artifacts.py`
Expected: PASS

**Step 5: Commit**

```bash
git add apps tests artifacts/modelling/data_model.md
git commit -m "feat(retrieval): add persistent hybrid sqlite retrieval"
```

### Task 13: Add live HTML/PDF fetching for non-RSS sources

**Issues:**
- `#137`

**Files:**
- Modify: `apps/agent/ingest/`
- Modify: `tests/agent/`
- Modify: `artifacts/modelling/source_registry.yaml` or related docs if needed

**Step 1: Write the failing ingestion tests**

Add tests asserting:
- live HTML and PDF fetch paths work for supported non-RSS sources
- metadata-only and paywall rules still hold
- fetch failures degrade cleanly without fabricated text

**Step 2: Run the ingestion-focused suite**

Run the relevant ingestion suite for the touched modules.
Expected: FAIL

**Step 3: Implement minimal live-fetch support**

Add the narrowest supported HTML/PDF live-fetch slice.

**Step 4: Re-run the ingestion-focused suite**

Run the same ingestion suite.
Expected: PASS

**Step 5: Commit**

```bash
git add apps tests artifacts/modelling/source_registry.yaml
git commit -m "feat(ingest): add live html and pdf fetching"
```

### Task 14: Finish alert delivery runtime after the daily-brief path is stable

**Issues:**
- `#74`

**Files:**
- Modify: `apps/agent/alerts/`
- Modify: `apps/agent/delivery/`
- Modify: `tests/agent/`
- Modify: `README.md` if supported commands change

**Step 1: Write the failing alert-delivery tests**

Add tests asserting:
- alert delivery respects cooldown and daily caps
- approved alerts can render and send through the supported runtime path
- alert delivery does not weaken the validated-evidence discipline established for the brief path

**Step 2: Run the alert suite**

Run the relevant alert-delivery suite.
Expected: FAIL

**Step 3: Implement minimal alert delivery runtime**

Add the smallest compliant alert-delivery slice after the brief contract is stable.

**Step 4: Re-run the alert suite**

Run the same alert suite.
Expected: PASS

**Step 5: Commit**

```bash
git add apps tests README.md
git commit -m "feat(alerts): complete alert delivery runtime"
```

### Task 15: Final verification gate for the full open-issue order

**Issues:**
- all currently open issues

**Files:**
- No new files; verification only

**Step 1: Run targeted daily-brief suites**

Run:
- `python -m unittest tests.agent.daily_brief.test_editorial_planner -v`
- `python -m unittest tests.agent.daily_brief.test_issue_retrieval -v`
- `python -m unittest tests.agent.daily_brief.test_openai_issue_planner -v`
- `python -m unittest tests.agent.daily_brief.test_openai_claim_composer -v`
- `python -m unittest tests.agent.daily_brief.test_synthesis -v`
- `python -m unittest tests.agent.daily_brief.test_runner -v`
- `python -m unittest tests.agent.delivery.test_html_report -v`
- `python -m unittest tests.agent.synthesis.test_postprocess -v`
- `python -m unittest tests.agent.daily_brief.test_critic -v`
- `python -m unittest tests.agent.validators.test_citation_validator -v`

**Step 2: Run evals and repo validators**

Run:
- `python -m unittest discover -s tests/evals -p "test_*.py" -v`
- `python scripts/validate_artifacts.py`
- `python scripts/validate_decision_record_schema.py`
- `python -m compileall -q apps tests scripts`

**Step 3: Run the broader repo suite**

Run:
- `python -m unittest discover -s tests -t . -p "test_*.py" -v`

Expected:
- all targeted and repo-wide suites pass
- no delivered HTML/email surface contains validator placeholder text
- brief-level abstain renders through the abstain template only
- the full open-issue queue has an explicit implemented-or-deferred position in the merged docs
