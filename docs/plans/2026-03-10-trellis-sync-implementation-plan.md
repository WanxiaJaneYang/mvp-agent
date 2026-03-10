# Trellis Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align the repo's Trellis workflow, skills, and specs with the current Python codebase and remove misleading defaults.

**Architecture:** Update Trellis-facing docs and skills first, then change session-recording behavior so journal updates do not create hidden commits by default. Fill the backend spec set with concrete Python conventions, add the missing referenced spec files, and mark frontend guidance as out-of-scope until frontend code exists.

**Tech Stack:** Markdown, Python 3.11+, Trellis workflow scripts

---

### Task 1: Plan and Scope

**Files:**
- Create: `docs/plans/2026-03-10-trellis-sync-implementation-plan.md`
- Modify: `AGENTS.md`
- Modify: `.trellis/workflow.md`

**Step 1: Confirm scope from the Trellis audit**

Review the existing Trellis audit and extract the required sync items:
- commit-policy drift
- hidden auto-commit behavior
- missing referenced spec files
- missing slash-command installation
- placeholder backend/frontend specs

**Step 2: Keep the AGENTS Trellis block but remove the missing slash-command assumption**

Change the managed Trellis intro so it points agents at the Trellis workflow/docs directly instead of requiring `/trellis:start`.

**Step 3: Update the workflow narrative**

Rewrite `.trellis/workflow.md` so it:
- no longer promises missing `/trellis:*` commands
- separates session recording from git commit behavior
- documents the repo's Python verification commands

### Task 2: Make Session Recording Safe by Default

**Files:**
- Modify: `.trellis/config.yaml`
- Modify: `.trellis/scripts/common/config.py`
- Modify: `.trellis/scripts/add_session.py`
- Modify: `.agents/skills/record-session/SKILL.md`

**Step 1: Add a config-backed default for session auto-commit**

Introduce a repo-level config flag that defaults journal recording to no auto-commit.

**Step 2: Update the session-recording script**

Make `add_session.py` default to the config value and add an explicit opt-in flag for auto-commit.

**Step 3: Update the recording skill**

Document planning-session usage with `--commit "-"` and explain that workspace auto-commit is opt-in only.

### Task 3: Sync Trellis Skills and Workflow References

**Files:**
- Modify: `.agents/skills/finish-work/SKILL.md`
- Modify: `.agents/skills/check-cross-layer/SKILL.md`
- Modify: `.agents/skills/before-backend-dev/SKILL.md`
- Modify: `.agents/skills/check-backend/SKILL.md`
- Create: `.trellis/spec/backend/type-safety.md`
- Create: `.trellis/spec/guides/pre-implementation-checklist.md`
- Modify: `.trellis/spec/backend/index.md`
- Modify: `.trellis/spec/guides/index.md`

**Step 1: Replace JS-first quality defaults**

Rewrite `finish-work` to use the repo's Python validation flow and current review expectations.

**Step 2: Resolve broken spec links**

Create the missing backend type-safety spec and pre-implementation checklist, then update indexes and dependent skills.

### Task 4: Replace Placeholder Specs with Repo Reality

**Files:**
- Modify: `.trellis/spec/backend/directory-structure.md`
- Modify: `.trellis/spec/backend/database-guidelines.md`
- Modify: `.trellis/spec/backend/error-handling.md`
- Modify: `.trellis/spec/backend/logging-guidelines.md`
- Modify: `.trellis/spec/backend/quality-guidelines.md`
- Modify: `.trellis/spec/frontend/index.md`
- Modify: `.trellis/spec/frontend/directory-structure.md`
- Modify: `.trellis/spec/frontend/component-guidelines.md`
- Modify: `.trellis/spec/frontend/hook-guidelines.md`
- Modify: `.trellis/spec/frontend/state-management.md`
- Modify: `.trellis/spec/frontend/type-safety.md`
- Modify: `.trellis/spec/frontend/quality-guidelines.md`
- Modify: `.trellis/worktree.yaml`

**Step 1: Fill backend specs with concrete examples**

Use actual code from `apps/agent`, `tests/agent`, and `scripts/` to document:
- package layout
- typed dataclass/enum usage
- error raising patterns
- current logging stance
- CI and local verification expectations
- current SQLite/database status

**Step 2: Mark frontend guidance as intentionally deferred**

Document that the repo currently has no frontend source tree and that agents should not invent frontend conventions yet.

**Step 3: Align worktree defaults with repo practice**

Point Trellis worktrees at `.worktrees/` and configure Python verification commands that match CI.

### Task 5: Verify

**Files:**
- Modify: `.trellis/tasks/00-bootstrap-guidelines/prd.md`

**Step 1: Update the active bootstrap task text if it still advertises outdated slash-command behavior**

Keep the active task aligned with the new Trellis workflow language.

**Step 2: Run targeted verification**

Run:
- `python -m compileall -q .trellis\scripts`
- `python .\.trellis\scripts\get_context.py`
- `python .\.trellis\scripts\add_session.py --help`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Expected:
- Trellis scripts still compile
- session context still renders
- add-session help shows the new explicit auto-commit flag
- repo test suite stays green after docs/script changes
