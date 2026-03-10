# Issue #35 Eval Harness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the current eval harness so it validates retrieval ordering and abstain/postprocess behavior in addition to citation validation.

**Architecture:** Preserve the existing golden-case runner and add narrow case-type dispatch instead of creating a separate eval framework. Keep all cases deterministic and offline-friendly so they remain fast in CI and local development.

**Tech Stack:** Python 3.11+, `json`, `pathlib`, `unittest`

---

### Task 1: Add eval-runner tests for new case types

**Files:**
- Create: `tests/evals/test_run_eval_suite.py`

**Step 1: Write the failing test**

Add tests asserting:
- unknown case types still fail clearly
- `retrieval` cases dispatch and validate expected ordering
- `postprocess` cases dispatch and validate final abstain output

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.evals.test_run_eval_suite -v`
Expected: FAIL because the eval runner does not expose the required helpers or behaviors yet.

**Step 3: Write minimal implementation shape**

Add the smallest test-facing hooks or refactors needed in `evals/run_eval_suite.py` so the runner logic is callable from tests.

**Step 4: Run test to verify it still fails for missing behavior**

Run: `python -m unittest tests.evals.test_run_eval_suite -v`
Expected: FAIL on behavioral assertions rather than import errors.

**Step 5: Commit**

```bash
git add tests/evals/test_run_eval_suite.py evals/run_eval_suite.py
git commit -m "test(evals): scaffold multi-type eval runner coverage"
```

### Task 2: Implement retrieval and postprocess case dispatch

**Files:**
- Modify: `evals/run_eval_suite.py`
- Modify: `tests/evals/test_run_eval_suite.py`

**Step 1: Write the next failing test**

Add assertions for:
- retrieval case expected pack size
- postprocess case expected abstain reason and status

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.evals.test_run_eval_suite -v`
Expected: FAIL because the new case evaluators are incomplete.

**Step 3: Write minimal implementation**

Implement:
- retrieval-case execution via `build_evidence_pack`
- postprocess-case execution via `finalize_validation_outcome`
- common failure formatting

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.evals.test_run_eval_suite -v`
Expected: PASS

**Step 5: Commit**

```bash
git add evals/run_eval_suite.py tests/evals/test_run_eval_suite.py
git commit -m "feat(evals): add retrieval and postprocess eval coverage"
```

### Task 3: Add golden fixtures and README updates

**Files:**
- Create: `evals/golden/case11.json`
- Create: `evals/golden/case12.json`
- Modify: `evals/README.md`

**Step 1: Write the failing test**

Add tests or assertions that the new golden fixtures are loadable and that README-documented case types match actual runner support.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.evals.test_run_eval_suite -v`
Expected: FAIL because fixtures or docs are missing.

**Step 3: Write minimal implementation**

Add:
- one retrieval golden case
- one postprocess golden case
- README documentation for supported case types
- explicit TODO note for future chained retrieval -> validation -> abstain evals

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.evals.test_run_eval_suite -v`
Expected: PASS

**Step 5: Commit**

```bash
git add evals/golden/case11.json evals/golden/case12.json evals/README.md tests/evals/test_run_eval_suite.py
git commit -m "docs(evals): add golden coverage for retrieval and abstain"
```

### Task 4: Full verification and progress logging

**Files:**
- Modify: `claude-progress.txt`

**Step 1: Update progress log**

Append the eval-harness extension summary, verification commands, and next step to `claude-progress.txt`.

**Step 2: Run verification**

Run:
- `python -m unittest tests.evals.test_run_eval_suite -v`
- `python evals/run_eval_suite.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `python -m compileall -q apps tests scripts evals`

Expected:
- eval-runner tests PASS
- golden suite PASS
- full suite PASS
- compile check PASS

**Step 3: Commit**

```bash
git add claude-progress.txt
git commit -m "docs: log eval harness extension progress"
```

