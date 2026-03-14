# Daily Brief Integrity Agent Rollout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Land daily-brief integrity issues `#160` through `#166` through a planning-first, issue-by-issue execution flow where every implementation issue gets its own branch, PR, review cycle, and merge.

**Architecture:** Treat the work as a dependency-managed rollout instead of one implementation stream. Land a docs-only planning PR first, then execute issue branches in merge order with only limited parallelism where file overlap is low.

**Tech Stack:** Python 3.11+, `unittest`, GitHub issues/PRs via `gh`, Trellis planning docs under `docs/plans/`

**Planning Issue:** `#167`

---

### Task 1: Create and land the planning issue/PR

**Files:**
- Create: `docs/plans/2026-03-14-daily-brief-integrity-agent-rollout-design.md`
- Create: `docs/plans/2026-03-14-daily-brief-integrity-agent-rollout-implementation-plan.md`

**Issue/Branch/PR:**
- Issue: planning issue for `#160-#166`
- Branch: `plan/daily-brief-integrity-160-166`
- PR: docs-only PR into `master`

**Step 1: Verify the planning issue exists**

Run:

```bash
gh issue list --state open --limit 20
```

Expected:
- one open planning issue for the `#160-#166` rollout exists

**Step 2: Create the planning branch/worktree**

Run:

```bash
git fetch origin
git worktree add .worktrees/plan-daily-brief-integrity-160-166 -b plan/daily-brief-integrity-160-166 origin/master
```

Expected:
- a clean docs-only worktree exists for the planning PR

**Step 3: Add or update the rollout docs**

Document:
- dependency order
- branch names
- PR boundaries
- review gates
- safe parallel windows

**Step 4: Run doc/artifact validation if touched surfaces require it**

Run:

```bash
python scripts/validate_artifacts.py
```

Expected:
- PASS

**Step 5: Commit and open the planning PR**

Run:

```bash
git add docs/plans/2026-03-14-daily-brief-integrity-agent-rollout-design.md docs/plans/2026-03-14-daily-brief-integrity-agent-rollout-implementation-plan.md
git commit -m "docs(plan): map issue-by-issue rollout for daily-brief integrity fixes"
gh pr create --base master --title "docs(plan): map issue-by-issue rollout for daily-brief integrity fixes" --body "Closes <planning-issue-number>"
```

Expected:
- one docs-only planning PR exists

### Task 2: Execute issue `#163` on its own branch

**Files:**
- Modify: `apps/agent/daily_brief/editorial_planner.py`
- Modify: `apps/agent/daily_brief/runner.py`
- Modify: `tests/agent/daily_brief/test_editorial_planner.py`
- Modify: `tests/agent/daily_brief/test_runner.py`
- Modify: `evals/` if the issue lands a malformed-thesis fixture immediately

**Issue/Branch/PR:**
- Issue: `#163`
- Branch: `fix/163-bottom-line-hardening`
- PR: one PR that closes `#163`

**Step 1: Create a clean worktree from updated master**

Run:

```bash
git fetch origin
git worktree add .worktrees/issue-163 -b fix/163-bottom-line-hardening origin/master
```

Expected:
- the branch starts from merged planning docs and current `master`

**Step 2: Write the failing tests**

Add tests for:
- bottom-line text derived from retained issue/thesis output
- malformed thesis fallback
- no direct token-bundle sentence output

**Step 3: Run the targeted suites**

Run:

```bash
python -m unittest tests.agent.daily_brief.test_editorial_planner tests.agent.daily_brief.test_runner -v
```

Expected:
- FAIL before the implementation

**Step 4: Implement the minimal fix**

Keep the branch scoped to:
- planner thesis generation
- runner wiring required by the issue

Do not include retrieval, validator, or delivery-state fixes.

**Step 5: Re-run tests, commit, and open PR**

Run:

```bash
python -m unittest tests.agent.daily_brief.test_editorial_planner tests.agent.daily_brief.test_runner -v
git add apps/agent/daily_brief/editorial_planner.py apps/agent/daily_brief/runner.py tests/agent/daily_brief/test_editorial_planner.py tests/agent/daily_brief/test_runner.py
git commit -m "fix(daily-brief): harden bottom-line generation"
gh pr create --base master --title "fix(daily-brief): harden bottom-line generation" --body "Closes #163"
```

Expected:
- one PR exists for `#163` only

### Task 3: Execute issue `#161` after `#163` merges

**Files:**
- Modify: `apps/agent/synthesis/postprocess.py`
- Modify: `apps/agent/delivery/html_report.py`
- Modify: `apps/agent/daily_brief/runner.py`
- Modify: `tests/agent/synthesis/test_postprocess.py`
- Modify: `tests/agent/delivery/test_html_report.py`
- Modify: `tests/agent/daily_brief/test_runner.py`

**Issue/Branch/PR:**
- Issue: `#161`
- Branch: `fix/161-abstain-render-state`
- PR: one PR that closes `#161`

**Step 1: Create the issue worktree from current master**

Run:

```bash
git fetch origin
git worktree add .worktrees/issue-161 -b fix/161-abstain-render-state origin/master
```

**Step 2: Write failing tests for abstain-state closure**

Add tests for:
- abstain-only UI rendering
- `meta.status=abstained` precedence
- header/body semantic consistency

**Step 3: Run the targeted suites**

Run:

```bash
python -m unittest tests.agent.synthesis.test_postprocess tests.agent.delivery.test_html_report tests.agent.daily_brief.test_runner -v
```

Expected:
- FAIL

**Step 4: Implement only the abstain/render-state closure**

Do not include placeholder suppression or fixture/live parity in this branch.

**Step 5: Re-run tests, commit, and open PR**

Run:

```bash
python -m unittest tests.agent.synthesis.test_postprocess tests.agent.delivery.test_html_report tests.agent.daily_brief.test_runner -v
git add apps/agent/synthesis/postprocess.py apps/agent/delivery/html_report.py apps/agent/daily_brief/runner.py tests/agent/synthesis/test_postprocess.py tests/agent/delivery/test_html_report.py tests/agent/daily_brief/test_runner.py
git commit -m "fix(delivery): close abstain render-state"
gh pr create --base master --title "fix(delivery): close abstain render-state" --body "Closes #161"
```

### Task 4: Execute issue `#164` after `#163` merges

**Files:**
- Modify: `apps/agent/daily_brief/issue_retrieval.py`
- Modify: `apps/agent/daily_brief/openai_issue_planner.py`
- Modify: `apps/agent/daily_brief/openai_claim_composer.py`
- Modify: `tests/agent/daily_brief/test_issue_retrieval.py`
- Modify: `tests/agent/daily_brief/test_openai_issue_planner.py`
- Modify: `tests/agent/daily_brief/test_openai_claim_composer.py`

**Issue/Branch/PR:**
- Issue: `#164`
- Branch: `feat/164-semantic-issue-scoping`
- PR: one PR that closes `#164`

**Step 1: Create the worktree from current master**

Run:

```bash
git fetch origin
git worktree add .worktrees/issue-164 -b feat/164-semantic-issue-scoping origin/master
```

**Step 2: Write failing tests**

Add tests for:
- minimum semantic separation across buckets
- no cross-issue evidence borrowing
- bucket-to-claim consistency

**Step 3: Run the targeted suites**

Run:

```bash
python -m unittest tests.agent.daily_brief.test_issue_retrieval tests.agent.daily_brief.test_openai_issue_planner tests.agent.daily_brief.test_openai_claim_composer -v
```

Expected:
- FAIL

**Step 4: Implement only semantic scoping**

Do not include entailment gating or eval-suite expansion in this branch.

**Step 5: Re-run tests, commit, and open PR**

Run:

```bash
python -m unittest tests.agent.daily_brief.test_issue_retrieval tests.agent.daily_brief.test_openai_issue_planner tests.agent.daily_brief.test_openai_claim_composer -v
git add apps/agent/daily_brief/issue_retrieval.py apps/agent/daily_brief/openai_issue_planner.py apps/agent/daily_brief/openai_claim_composer.py tests/agent/daily_brief/test_issue_retrieval.py tests/agent/daily_brief/test_openai_issue_planner.py tests/agent/daily_brief/test_openai_claim_composer.py
git commit -m "feat(retrieval): strengthen semantic issue scoping"
gh pr create --base master --title "feat(retrieval): strengthen semantic issue scoping" --body "Closes #164"
```

### Task 5: Execute issue `#162` after `#161` merges

**Files:**
- Modify: `apps/agent/validators/citation_validator.py`
- Modify: `apps/agent/synthesis/postprocess.py`
- Modify: `apps/agent/delivery/html_report.py`
- Modify: `tests/agent/validators/test_citation_validator.py`
- Modify: `tests/agent/synthesis/test_postprocess.py`
- Modify: `tests/agent/delivery/test_html_report.py`

**Issue/Branch/PR:**
- Issue: `#162`
- Branch: `fix/162-placeholder-suppression`
- PR: one PR that closes `#162`

**Step 1: Create the worktree from current master**

Run:

```bash
git fetch origin
git worktree add .worktrees/issue-162 -b fix/162-placeholder-suppression origin/master
```

**Step 2: Write failing tests**

Add tests for:
- no placeholder text in user-facing HTML/email
- placeholders preserved only in internal artifacts/debug surfaces if still needed
- render-policy coverage for partial/abstain/hold states

**Step 3: Run the targeted suites**

Run:

```bash
python -m unittest tests.agent.validators.test_citation_validator tests.agent.synthesis.test_postprocess tests.agent.delivery.test_html_report -v
```

Expected:
- FAIL

**Step 4: Implement only placeholder suppression**

Do not include fixture/live parity or entailment gating in this branch.

**Step 5: Re-run tests, commit, and open PR**

Run:

```bash
python -m unittest tests.agent.validators.test_citation_validator tests.agent.synthesis.test_postprocess tests.agent.delivery.test_html_report -v
git add apps/agent/validators/citation_validator.py apps/agent/synthesis/postprocess.py apps/agent/delivery/html_report.py tests/agent/validators/test_citation_validator.py tests/agent/synthesis/test_postprocess.py tests/agent/delivery/test_html_report.py
git commit -m "fix(delivery): suppress validator placeholders in final artifacts"
gh pr create --base master --title "fix(delivery): suppress validator placeholders in final artifacts" --body "Closes #162"
```

### Task 6: Execute issue `#160` after `#161` and `#162` merge

**Files:**
- Modify: `scripts/run_daily_brief_fixture.py`
- Modify: `scripts/run_daily_brief.py`
- Modify: `apps/agent/daily_brief/runner.py`
- Modify: `tests/agent/daily_brief/test_runner.py`
- Modify: `README.md`
- Modify: `artifacts/modelling/pipeline.md`

**Issue/Branch/PR:**
- Issue: `#160`
- Branch: `fix/160-fixture-live-publish-gate-parity`
- PR: one PR that closes `#160`

**Step 1: Create the worktree from current master**

Run:

```bash
git fetch origin
git worktree add .worktrees/issue-160 -b fix/160-fixture-live-publish-gate-parity origin/master
```

**Step 2: Write failing parity tests**

Add tests for:
- fixture/live publish-summary parity
- explicit `analytical_status=not_run` if critic remains optional
- provider demo hold/publish parity

**Step 3: Run the targeted suites**

Run:

```bash
python -m unittest tests.agent.daily_brief.test_runner -v
```

Expected:
- FAIL

**Step 4: Implement only fixture/live parity**

Do not reopen abstain-render behavior or validator placeholder policy here.

**Step 5: Re-run tests, validate docs if touched, commit, and open PR**

Run:

```bash
python -m unittest tests.agent.daily_brief.test_runner -v
python scripts/validate_artifacts.py
git add scripts/run_daily_brief_fixture.py scripts/run_daily_brief.py apps/agent/daily_brief/runner.py tests/agent/daily_brief/test_runner.py README.md artifacts/modelling/pipeline.md
git commit -m "fix(demo): align fixture and live publish-gate behavior"
gh pr create --base master --title "fix(demo): align fixture and live publish-gate behavior" --body "Closes #160"
```

### Task 7: Execute issue `#165` after `#164` and `#162` merge

**Files:**
- Modify: `apps/agent/validators/citation_validator.py`
- Modify: `apps/agent/daily_brief/critic.py`
- Modify: `apps/agent/daily_brief/openai_claim_composer.py`
- Modify: `tests/agent/validators/test_citation_validator.py`
- Modify: `tests/agent/daily_brief/test_critic.py`
- Modify: `tests/agent/daily_brief/test_openai_claim_composer.py`
- Modify: `evals/`
- Modify: `tests/evals/`

**Issue/Branch/PR:**
- Issue: `#165`
- Branch: `feat/165-claim-citation-entailment-gate`
- PR: one PR that closes `#165`

**Step 1: Create the worktree from current master**

Run:

```bash
git fetch origin
git worktree add .worktrees/issue-165 -b feat/165-claim-citation-entailment-gate origin/master
```

**Step 2: Write failing tests and evals**

Add coverage for:
- claim-to-citation entailment
- same-thesis consistency across counter/minority/watch claims
- templated or empty `why_it_matters`

**Step 3: Run the targeted suites**

Run:

```bash
python -m unittest tests.agent.validators.test_citation_validator tests.agent.daily_brief.test_critic tests.agent.daily_brief.test_openai_claim_composer -v
python -m unittest discover -s tests/evals -p "test_*.py" -v
```

Expected:
- FAIL

**Step 4: Implement only entailment gating**

Do not add broad demo/regression scaffolding beyond what the issue itself requires.

**Step 5: Re-run tests, commit, and open PR**

Run:

```bash
python -m unittest tests.agent.validators.test_citation_validator tests.agent.daily_brief.test_critic tests.agent.daily_brief.test_openai_claim_composer -v
python -m unittest discover -s tests/evals -p "test_*.py" -v
git add apps/agent/validators/citation_validator.py apps/agent/daily_brief/critic.py apps/agent/daily_brief/openai_claim_composer.py tests/agent/validators/test_citation_validator.py tests/agent/daily_brief/test_critic.py tests/agent/daily_brief/test_openai_claim_composer.py evals tests/evals
git commit -m "feat(validation): add claim-citation entailment gating"
gh pr create --base master --title "feat(validation): add claim-citation entailment gating" --body "Closes #165"
```

### Task 8: Execute issue `#166` after `#160` and `#165` merge

**Files:**
- Modify: `evals/`
- Modify: `tests/evals/`
- Modify: `tests/agent/daily_brief/test_runner.py`
- Modify: `tests/agent/delivery/test_html_report.py`
- Modify: `tests/agent/synthesis/test_postprocess.py`
- Modify: `tests/agent/validators/test_citation_validator.py`
- Modify: `tests/agent/daily_brief/test_editorial_planner.py`
- Modify: `tests/agent/daily_brief/test_issue_retrieval.py`
- Modify: `README.md`

**Issue/Branch/PR:**
- Issue: `#166`
- Branch: `test/166-daily-brief-regression-fixtures`
- PR: one PR that closes `#166`

**Step 1: Create the worktree from current master**

Run:

```bash
git fetch origin
git worktree add .worktrees/issue-166 -b test/166-daily-brief-regression-fixtures origin/master
```

**Step 2: Add failing regression fixtures**

Add stage-level demos/evals for:
- malformed bottom line
- cross-issue leakage
- abstain render closure
- placeholder suppression
- fixture/live parity

**Step 3: Run the targeted regression suites**

Run:

```bash
python -m unittest discover -s tests/evals -p "test_*.py" -v
python -m unittest tests.agent.daily_brief.test_runner tests.agent.delivery.test_html_report tests.agent.synthesis.test_postprocess tests.agent.validators.test_citation_validator tests.agent.daily_brief.test_editorial_planner tests.agent.daily_brief.test_issue_retrieval -v
```

Expected:
- FAIL before the fixtures and expectations are fully wired

**Step 4: Implement only the regression/eval lock-in**

Do not reopen planner, retrieval, delivery, or validator behavior except where test fixtures require aligned expected outputs.

**Step 5: Re-run tests, update docs if needed, commit, and open PR**

Run:

```bash
python -m unittest discover -s tests/evals -p "test_*.py" -v
python -m unittest tests.agent.daily_brief.test_runner tests.agent.delivery.test_html_report tests.agent.synthesis.test_postprocess tests.agent.validators.test_citation_validator tests.agent.daily_brief.test_editorial_planner tests.agent.daily_brief.test_issue_retrieval -v
git add evals tests/evals tests/agent/daily_brief/test_runner.py tests/agent/delivery/test_html_report.py tests/agent/synthesis/test_postprocess.py tests/agent/validators/test_citation_validator.py tests/agent/daily_brief/test_editorial_planner.py tests/agent/daily_brief/test_issue_retrieval.py README.md
git commit -m "test(daily-brief): add stage-level regression fixtures"
gh pr create --base master --title "test(daily-brief): add stage-level regression fixtures" --body "Closes #166"
```

### Task 9: Run merge-gate verification after each implementation PR

**Files:**
- No new files

**Step 1: Check PR status**

Run:

```bash
gh pr checks <pr-number>
gh pr view <pr-number> --comments
```

Expected:
- CI passes
- unresolved review comments are visible

**Step 2: Address comments on the same issue branch**

Rules:
- keep the branch scoped to its issue
- do not absorb a neighboring issue's work during review cleanup

**Step 3: Merge only after approval and green checks**

Run:

```bash
gh pr merge <pr-number> --merge --delete-branch
```

Expected:
- the issue closes through the PR
- `master` becomes the base for the next dependent issue

### Task 10: Run final integrity verification after `#166` merges

**Files:**
- No new files

**Step 1: Run targeted daily-brief suites**

Run:

```bash
python -m unittest tests.agent.daily_brief.test_editorial_planner tests.agent.daily_brief.test_issue_retrieval tests.agent.daily_brief.test_openai_issue_planner tests.agent.daily_brief.test_openai_claim_composer tests.agent.daily_brief.test_runner tests.agent.daily_brief.test_critic tests.agent.delivery.test_html_report tests.agent.synthesis.test_postprocess tests.agent.validators.test_citation_validator -v
```

Expected:
- PASS

**Step 2: Run evals and repo validators**

Run:

```bash
python -m unittest discover -s tests/evals -p "test_*.py" -v
python scripts/validate_artifacts.py
python scripts/validate_decision_record_schema.py
python -m compileall -q apps tests scripts
```

Expected:
- PASS

**Step 3: Run the broader repo suite**

Run:

```bash
python -m unittest discover -s tests -t . -p "test_*.py" -v
```

Expected:
- PASS
- no placeholder text in delivered artifact tests
- abstain-only output remains closed under delivery
- fixture/live parity remains covered
