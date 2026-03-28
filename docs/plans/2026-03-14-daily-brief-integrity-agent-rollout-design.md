# Daily Brief Integrity Agent Rollout Design

## Goal

Turn daily-brief integrity issues `#160` through `#166` into an execution program that an agent team can run without violating the repo rule of `issue -> PR -> merge`.

Planning tracker:
- `#167` `[Plan][P0] Plan issue-by-issue rollout for daily-brief integrity fixes #160-#166`

## Constraints

- Each implementation issue must have its own branch, PR, review cycle, and merge.
- Do not combine `#160-#166` into one implementation branch.
- Do not stack dependent implementation PRs on top of unmerged implementation branches.
- Start each implementation branch from updated `master` after its prerequisites merge.
- Keep planning as a separate docs-only step before any implementation branch is opened.

## Problem Shape

The seven issues are not equally parallel-safe.

- `#160`, `#161`, and `#162` are delivery-state and publish-state closure work.
- `#163`, `#164`, and `#165` are upstream analysis-quality hardening work.
- `#166` is the regression and eval lock-in tail.

They overlap across:

- `apps/agent/daily_brief/runner.py`
- `apps/agent/delivery/html_report.py`
- `apps/agent/synthesis/postprocess.py`
- `apps/agent/validators/citation_validator.py`
- `apps/agent/daily_brief/openai_claim_composer.py`
- `tests/agent/daily_brief/test_runner.py`
- `tests/agent/delivery/test_html_report.py`

That overlap means the agent team should be organized around merge boundaries, not around maximum raw concurrency.

## Recommended Execution Order

1. Planning issue/PR first
2. `#163` Harden Bottom line generation and stop token-bundle prose
3. `#161` Close abstain render-state so delivery cannot render invalid body content
4. `#164` Upgrade issue evidence scopes from lexical bucketing to semantic scoping
5. `#162` Keep validator placeholders out of final HTML and email
6. `#160` Align fixture/demo and live publish-gate behavior
7. `#165` Add claim-citation entailment gating beyond citation coverage
8. `#166` Add stage-level daily-brief demos/evals and fine-grained regression fixtures

## Why This Order

### `#163` first

`#163` stabilizes bottom-line generation at the planner layer. Later regression fixtures in `#166` should lock in the corrected behavior, not the current token-bundle output. It also reduces the risk that renderer-focused work bakes in malformed bottom-line assumptions.

### `#161` before `#162` and `#160`

`#161` defines the correct abstain and hold render-state contract. `#162` then narrows that finalized contract by suppressing validator placeholders. `#160` should not be implemented until that publish-state model is stable, otherwise fixture/live parity tests will be written against shifting semantics.

### `#164` before `#165`

`#164` improves issue evidence semantics and claim input quality. `#165` is stricter analytical validation and entailment gating. It should evaluate the stronger scoping model, not the current lexical approximation.

### `#166` last

`#166` is the lock-in tail. It should encode the settled behavior from `#160-#165` and should not churn while the upstream contract is still moving.

## Parallel-Safe Windows

### Wave 0

Planning docs only. No implementation branches.

### Wave 1

`#163` alone.

Reason:
- it touches planner semantics and likely `tests/agent/daily_brief/test_runner.py`
- starting it alone keeps the first merge boundary clean

### Wave 2

`#161` and `#164` can run in parallel after `#163` merges.

Reason:
- `#161` is centered on postprocess, delivery, and runner status closure
- `#164` is centered on issue retrieval, issue planner prompting, and claim-composer evidence binding
- they should still avoid opportunistic edits outside their issue surface

### Wave 3

`#162` can start after `#161` merges.

It may overlap in time with review or merge handling for `#164`, but not with another branch editing `citation_validator.py` or `html_report.py`.

### Wave 4

`#160` and `#165` can run in parallel after prerequisites merge:

- `#160` requires `#161` and `#162`
- `#165` requires `#164` and `#162`

Reason:
- `#160` is runner/scripts/demo parity work
- `#165` is validator/critic/claim-composer analytical gating work

### Wave 5

`#166` alone, after `#160` and `#165` merge.

## Branch and PR Policy

Each issue must use:

- one dedicated worktree
- one dedicated branch
- one PR referencing exactly that issue
- one review/merge cycle before the next dependent issue starts

Recommended branch names:

- planning: `plan/daily-brief-integrity-160-166`
- `#163`: `fix/163-bottom-line-hardening`
- `#161`: `fix/161-abstain-render-state`
- `#164`: `feat/164-semantic-issue-scoping`
- `#162`: `fix/162-placeholder-suppression`
- `#160`: `fix/160-fixture-live-publish-gate-parity`
- `#165`: `feat/165-claim-citation-entailment-gate`
- `#166`: `test/166-daily-brief-regression-fixtures`

PR policy:

- target branch is always `master`
- PR body should map code changes directly to the issue acceptance criteria
- do not stack implementation PRs on top of each other
- do not combine multiple issue numbers into one implementation PR

## Review Policy

Every issue PR should include:

- exact issue link in the PR description
- targeted tests run for the touched surface
- docs touched if behavior or contract changed
- a short reviewer checklist tied to issue acceptance criteria

Review focus by issue:

- `#163`: planner contract, fallback quality, bottom-line provenance
- `#161`: abstain closure and header/body semantic consistency
- `#164`: issue-local evidence binding and anti-leakage guarantees
- `#162`: no user-facing placeholders in HTML/email
- `#160`: fixture/live parity and critic handling symmetry
- `#165`: analytical validation depth and entailment evidence
- `#166`: regression coverage quality and CI/local run clarity

## Verification Policy

Every issue PR must run targeted tests for the touched modules before review.

Additionally:

- any doc-surface contract change should run `python scripts/validate_artifacts.py`
- any decision-record schema change should run `python scripts/validate_decision_record_schema.py`
- the planning PR itself is docs-only and should at minimum validate docs/artifacts if touched

## Agent Team Model

Use the team in two roles:

- implementation agents for issue branches
- review/check agents that validate the current PR against issue acceptance criteria before merge

Do not keep multiple long-lived implementation agents active on overlapping branches. Start a fresh agent per issue branch after prerequisites merge.

## Success Criteria

The rollout is successful when:

- planning lands first as docs-only work
- each implementation issue has its own branch and PR
- dependent issues wait for prerequisite merges
- no issue is left as local-only work
- `#166` locks in the merged behavior from the prior six issues
