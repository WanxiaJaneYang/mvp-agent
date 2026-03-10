# Development Workflow

> Repo-specific Trellis workflow for `mvp-agent`.

---

## Quick Start

### 1. Initialize or confirm developer identity

```bash
python ./.trellis/scripts/get_developer.py
python ./.trellis/scripts/init_developer.py <your-name>
```

This creates:
- `.trellis/.developer`
- `.trellis/workspace/<developer>/`

### 2. Load current context

```bash
python ./.trellis/scripts/get_context.py
```

Check:
- current branch and worktree state
- active Trellis task
- current developer workspace

### 3. Read the right guidance before editing

Always read:
- `AGENTS.md`
- `CLAUDE.md`
- `.trellis/spec/backend/index.md`
- `.trellis/spec/guides/index.md`

Read `.trellis/spec/frontend/index.md` only when the repo actually contains frontend code for the task. At the moment this repository is Python-first and the frontend specs are intentionally marked as not-yet-applicable.

---

## Repo Reality

This repository currently centers on:
- Python runtime and pipeline code under `apps/agent/`
- Python unit tests under `tests/agent/`
- modelling artifacts under `artifacts/modelling/`
- validation scripts under `scripts/`
- design/implementation plans under `docs/plans/`

The CI workflow is Python-based:

```bash
python scripts/validate_artifacts.py
python scripts/validate_decision_record_schema.py
python -m compileall -q apps tests scripts
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## Core Flow

Use the repo's normal implementation flow:

```text
explore -> plan -> code -> verify -> record
```

Where:
1. `explore` means read only the files needed for the task
2. `plan` means identify the exact files, contracts, and verification steps
3. `code` means make the smallest useful change
4. `verify` means run the relevant Python validators/tests
5. `record` means update Trellis task/workspace state

Git commits and MR work follow the current repo workflow and user instructions, but session recording must not create hidden commits by default.

---

## Task Workflow

### Create or continue a Trellis task

```bash
python ./.trellis/scripts/task.py list
python ./.trellis/scripts/task.py create "<title>" --slug <name>
```

If `get_context.py` shows an active task:
- read its `prd.md`
- confirm it still matches the work you are doing
- keep it open until the task is actually complete

### Research and implement

Before editing:
- read the relevant `.trellis/spec/` docs
- inspect existing code patterns in `apps/agent/`, `tests/agent/`, and `scripts/`
- for cross-layer work, read `.trellis/spec/guides/pre-implementation-checklist.md`

During implementation:
- keep changes small and local
- follow the current Python typing/dataclass/enum conventions
- keep modelling artifacts and runtime behavior aligned

### Verify

Minimum repo verification commands:

```bash
python scripts/validate_artifacts.py
python scripts/validate_decision_record_schema.py
python -m compileall -q apps tests scripts
python -m unittest discover -s tests -p "test_*.py" -v
```

Run the subset that matches the files you touched, and run the full suite when the change crosses multiple areas.

---

## Session Recording

Record Trellis progress with:

```bash
python ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "-" \
  --summary "Brief summary"
```

By default this:
1. appends to `.trellis/workspace/<developer>/journal-N.md`
2. updates `.trellis/workspace/<developer>/index.md`
3. leaves git state unchanged

If the current workflow explicitly wants Trellis metadata auto-committed, opt in:

```bash
python ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "abc1234" \
  --summary "Brief summary" \
  --auto-commit
```

---

## Session End

Before treating work as done:
- run the relevant verification commands
- update `.trellis/spec/` if the task changed conventions or executable contracts
- archive the Trellis task only when the task is actually complete
- record the session in `.trellis/workspace/`

Use these files directly for checklists:
- `.agents/skills/finish-work/SKILL.md`
- `.agents/skills/record-session/SKILL.md`
- `.agents/skills/check-cross-layer/SKILL.md`

---

## Common Commands

```bash
# Trellis context
python ./.trellis/scripts/get_context.py
python ./.trellis/scripts/get_context.py --mode record

# Task management
python ./.trellis/scripts/task.py list
python ./.trellis/scripts/task.py create "<title>" --slug <name>
python ./.trellis/scripts/task.py archive <name>

# Session recording
python ./.trellis/scripts/add_session.py --title "..." --commit "-" --summary "..."

# Repo verification
python scripts/validate_artifacts.py
python scripts/validate_decision_record_schema.py
python -m compileall -q apps tests scripts
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## Principles

- Read before write.
- Match actual repo patterns, not generic defaults.
- Keep backend guidance concrete and executable.
- Do not invent frontend conventions before frontend code exists.
- Keep Trellis recording separate from git commits unless explicitly requested.
