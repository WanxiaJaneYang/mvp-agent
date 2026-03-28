# Repo State Resolution Plan — 2026-03-28

## Problem Summary

Branch `feat/open-issues-main` contains finished, passing work that was never landed.
All 256 tests pass and 0 GitHub issues remain open, but four structural gaps block clean progress.

---

## Step 1 — Commit the uncommitted tracked changes

**What:** Stage and commit the 11 modified tracked files.

Files in scope:
- `README.md`
- `artifacts/PRD.md`
- `artifacts/modelling/data_model.md`
- `artifacts/modelling/citation_contract.md`
- `artifacts/modelling/pipeline.md`
- `artifacts/modelling/MODELLING_CHECKLIST.md`
- `artifacts/modelling/TODO.md`
- `artifacts/modelling/decision_record_schema.md`
- `.trellis/workspace/Lenovo/index.md`
- `.trellis/workspace/Lenovo/journal-1.md`
- `.claude/settings.local.json`

**Verify:** `git status` shows no modified tracked files after commit.

---

## Step 2 — Triage and commit (or discard) the untracked artifacts

**What:** Review each untracked file and decide: commit, gitignore, or delete.

Recommended disposition:
| File | Action |
|------|--------|
| `docs/plans/2026-03-*` (6 plan docs) | Commit — useful design history |
| `issue_121.md`, `issue_123.md`, `issue_139.md` | Delete — issues closed; content captured in GitHub |
| `.codex_issue_m002.md` | Delete — superseded |
| `findings.md`, `progress.md`, `task_plan.md` | Delete — ephemeral agent artifacts |
| `demo-show-brief.png` | Commit or gitignore as needed |

**Verify:** `git status` shows no untracked files except `.env`, `.budget_state.json`, and other intentionally-ignored paths.

---

## Step 3 — Open a PR to merge this branch into master

**What:** Push `feat/open-issues-main` to origin and open a pull request.

PR scope (95 files, ~10,000 lines):
- Daily brief redesign (runner, synthesis, FTS, evidence pack, HTML report)
- Alert delivery runtime
- Eval cases 18–22
- Repo Ops Dashboard (`tools/repo_dashboard/`)
- Supporting tests and documentation

**Verify:** CI is green on the PR; all 256 tests pass; PR description matches scope.

---

## Step 4 — Fix the Trellis workflow (non-blocking, do last)

**What:** Align `.trellis/` scaffolding with the actual Python repo.

Sub-tasks:
1. Remove or stub out references to missing spec files (`type-safety.md`, `pre-implementation-checklist.md`, etc.)
2. Rewrite `.trellis/spec/backend/*` to reflect Python CI commands (`ruff`, `mypy`, `pytest`)
3. Update `finish-work` skill to use Python-based verification steps
4. Mark frontend Trellis docs as out-of-scope until a frontend exists
5. Install or remove advertised `/trellis:*` commands from `.claude/commands`

**Verify:** No broken file references in `.trellis/`; `finish-work` skill matches actual CI.

---

## Execution order

```
Step 1 → Step 2 → Step 3 → Step 4
```

Steps 1 and 2 must precede Step 3 (clean commit history before PR).
Step 4 is independent and can be deferred.
