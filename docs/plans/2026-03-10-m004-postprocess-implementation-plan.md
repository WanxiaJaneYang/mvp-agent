# M004 Postprocess Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the missing post-validation synthesis helper that turns unrecoverable citation-validation failures into explicit abstain output.

**Architecture:** Keep the postprocess layer small and deterministic. It will transform stage-8 validation results into delivery-ready synthesis payloads without adding delivery or orchestrator complexity yet.

**Tech Stack:** Python 3.11+, `unittest`

---

### Task 1: Add abstain synthesis builder

**Files:**
- Create: `apps/agent/synthesis/postprocess.py`
- Create: `tests/agent/synthesis/test_postprocess.py`

**Step 1: Write the failing test**

Add a test asserting the abstain builder creates one explicit insufficient-evidence bullet for each core section.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.synthesis.test_postprocess -v`
Expected: FAIL because `apps.agent.synthesis.postprocess` does not exist.

**Step 3: Write minimal implementation**

Add a helper that builds deterministic abstain synthesis for:
- `prevailing`
- `counter`
- `minority`
- `watch`

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.synthesis.test_postprocess -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/synthesis/postprocess.py tests/agent/synthesis/test_postprocess.py
git commit -m "feat(synthesis): add abstain synthesis builder"
```

### Task 2: Add validation-outcome finalizer

**Files:**
- Modify: `apps/agent/synthesis/postprocess.py`
- Modify: `tests/agent/synthesis/test_postprocess.py`

**Step 1: Write the failing test**

Add tests asserting:
- `ok` status passes synthesis through unchanged
- `partial` status preserves degraded synthesis
- `retry` or failed validation maps to `abstained` with explicit abstain synthesis

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.synthesis.test_postprocess -v`
Expected: FAIL because the finalizer does not exist yet.

**Step 3: Write minimal implementation**

Add a postprocess helper that maps validation results into final synthesis payloads and final statuses.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.synthesis.test_postprocess -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/synthesis/postprocess.py tests/agent/synthesis/test_postprocess.py
git commit -m "feat(synthesis): finalize validation outcomes deterministically"
```

### Task 3: Full verification and progress logging

**Files:**
- Modify: `artifacts/modelling/backlog.json`
- Modify: `claude-progress.txt`

**Step 1: Update progress records**

Log the new postprocess slice in `claude-progress.txt` and, if this satisfies the repo's current M004 slice, update the backlog status accordingly.

**Step 2: Run verification**

Run:
- `python -m unittest tests.agent.synthesis.test_postprocess -v`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `python -m compileall -q apps tests scripts evals`
- `python scripts/validate_artifacts.py`

Expected:
- synthesis postprocess tests PASS
- full suite PASS
- compile check PASS
- artifact validation PASS

**Step 3: Commit**

```bash
git add artfacts/modelling/backlog.json claude-progress.txt
git commit -m "docs: log validation postprocess progress"
```
