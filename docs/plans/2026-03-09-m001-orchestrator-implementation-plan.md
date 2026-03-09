# M001 Orchestrator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first executable runtime skeleton for `M001` with shared run/stage contracts, a minimal orchestrator, and bounded retry behavior.

**Architecture:** Add a small orchestration layer that is independent from storage and domain-specific stages. The orchestrator will execute injected stages against a typed run context and emit lifecycle snapshots shaped like the `runs` table contract, so later persistence work can plug in without rewriting the execution core.

**Tech Stack:** Python 3.11+, `dataclasses`, `enum`, `unittest`

---

### Task 1: Add the first failing orchestrator test

**Files:**
- Create: `tests/agent/test_orchestrator.py`
- Create: `apps/agent/orchestrator.py`

**Step 1: Write the failing test**

Add a test that creates a no-op stage, runs `daily_brief`, and expects a lifecycle recorder to receive both `running` and `ok` snapshots with the correct `run_type`.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.test_orchestrator.OrchestratorTests.test_records_running_and_ok_lifecycle -v`
Expected: FAIL because `apps.agent.orchestrator` or `run_pipeline` does not exist.

**Step 3: Write minimal implementation**

Create `apps/agent/orchestrator.py` with a minimal `run_pipeline(...)` entry point sufficient to pass this test.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.test_orchestrator.OrchestratorTests.test_records_running_and_ok_lifecycle -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/agent/test_orchestrator.py apps/agent/orchestrator.py
git commit -m "feat(runtime): add minimal orchestrator lifecycle skeleton"
```

### Task 2: Add shared run and stage types

**Files:**
- Create: `apps/agent/pipeline/types.py`
- Create: `apps/agent/pipeline/stages.py`
- Modify: `apps/agent/orchestrator.py`
- Test: `tests/agent/test_orchestrator.py`

**Step 1: Write the failing test**

Add a test that asserts invalid run types raise an error and valid run types are normalized through shared types.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.test_orchestrator.OrchestratorTests.test_rejects_unknown_run_type -v`
Expected: FAIL because the shared type layer does not exist yet.

**Step 3: Write minimal implementation**

Add:
- `RunType`
- `RunStatus`
- `RunCounters`
- `RunContext`
- `StageResult`
- a small stage protocol

Wire the orchestrator to use them.

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.agent.test_orchestrator -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/agent/test_orchestrator.py apps/agent/orchestrator.py apps/agent/pipeline/types.py apps/agent/pipeline/stages.py
git commit -m "feat(runtime): add orchestrator run and stage contracts"
```

### Task 3: Add bounded retry behavior

**Files:**
- Modify: `apps/agent/orchestrator.py`
- Modify: `apps/agent/pipeline/stages.py`
- Test: `tests/agent/test_orchestrator.py`

**Step 1: Write the failing test**

Add one test where a retryable stage fails once then succeeds, and one test where retries are exhausted and the run fails.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.test_orchestrator.OrchestratorTests.test_retries_retryable_stage_until_success tests.agent.test_orchestrator.OrchestratorTests.test_fails_when_retry_limit_is_exhausted -v`
Expected: FAIL because retry handling is not implemented yet.

**Step 3: Write minimal implementation**

Add a fixed retry cap and a retryability signal in the stage result or stage error path. Keep retries local to a stage execution and never loop indefinitely.

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.agent.test_orchestrator -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/agent/test_orchestrator.py apps/agent/orchestrator.py apps/agent/pipeline/stages.py
git commit -m "feat(runtime): add bounded stage retry handling"
```

### Task 4: Add budget-stop and partial-status propagation

**Files:**
- Modify: `apps/agent/orchestrator.py`
- Test: `tests/agent/test_orchestrator.py`

**Step 1: Write the failing test**

Add tests ensuring:
- a budget-stop signal produces `stopped_budget`
- a partial stage result produces final `partial` status when no later hard failure occurs

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.test_orchestrator.OrchestratorTests.test_budget_stop_sets_stopped_budget_status tests.agent.test_orchestrator.OrchestratorTests.test_partial_stage_result_sets_partial_status -v`
Expected: FAIL because status propagation is incomplete.

**Step 3: Write minimal implementation**

Extend the orchestrator’s final-status logic without adding unrelated persistence or domain behavior.

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.agent.test_orchestrator -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/agent/test_orchestrator.py apps/agent/orchestrator.py
git commit -m "feat(runtime): propagate budget-stop and partial run outcomes"
```

### Task 5: Full verification and progress logging

**Files:**
- Modify: `claude-progress.txt`

**Step 1: Update progress log**

Append the implementation summary, validation commands, and next step to `claude-progress.txt`.

**Step 2: Run verification**

Run:
- `python -m unittest tests.agent.test_orchestrator -v`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `python -m compileall -q apps tests scripts evals`

Expected:
- orchestrator tests PASS
- full suite PASS
- compile check PASS

**Step 3: Commit**

```bash
git add claude-progress.txt
git commit -m "docs: log orchestrator skeleton progress"
```
