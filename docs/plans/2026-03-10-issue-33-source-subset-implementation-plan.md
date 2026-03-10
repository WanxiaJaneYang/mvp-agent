# Issue #33 V1 Active Source Subset Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a US-first runtime source subset artifact and a helper that resolves it against the full source registry so downstream work can target a stable v1 scope.

**Architecture:** Keep the full modelling registry unchanged and add a small runtime allowlist artifact plus a deterministic resolver helper. This preserves long-term catalogue coverage while giving the runtime path a narrow, testable source-of-truth.

**Tech Stack:** Python 3.11+, `pathlib`, `yaml`, `unittest`

---

### Task 1: Add source-scope tests

**Files:**
- Create: `tests/agent/runtime/test_source_scope.py`

**Step 1: Write the failing test**

Add tests asserting:
- the helper resolves the configured active source IDs in order
- the resolved subset contains the expected five source IDs
- a missing source ID in an allowlist input raises `ValueError`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.runtime.test_source_scope -v`
Expected: FAIL because `apps.agent.runtime.source_scope` does not exist.

**Step 3: Write minimal implementation shape**

Create a module stub with public functions such as:

```python
def load_source_registry(*, registry_path=None):
    raise NotImplementedError

def load_active_source_subset(*, registry_path=None, active_ids_path=None):
    raise NotImplementedError
```

**Step 4: Run test to verify it still fails for missing behavior**

Run: `python -m unittest tests.agent.runtime.test_source_scope -v`
Expected: FAIL on `NotImplementedError` or assertion mismatch rather than import failure.

**Step 5: Commit**

```bash
git add tests/agent/runtime/test_source_scope.py apps/agent/runtime/source_scope.py
git commit -m "test(runtime): scaffold active source subset coverage"
```

### Task 2: Add runtime subset artifact and resolver

**Files:**
- Create: `artifacts/runtime/v1_active_sources.yaml`
- Create: `apps/agent/runtime/source_scope.py`
- Modify: `tests/agent/runtime/test_source_scope.py`

**Step 1: Write the next failing test**

Add assertions for:
- one metadata-only source is included
- at least three official Tier 1 sources are included
- the helper returns full source records, not just IDs

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.runtime.test_source_scope -v`
Expected: FAIL because the artifact or resolver behavior is incomplete.

**Step 3: Write minimal implementation**

Implement:
- full source-registry loading from YAML
- active allowlist loading from YAML
- source resolution with stable order and missing-ID validation

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.runtime.test_source_scope -v`
Expected: PASS

**Step 5: Commit**

```bash
git add artifacts/runtime/v1_active_sources.yaml apps/agent/runtime/source_scope.py tests/agent/runtime/test_source_scope.py
git commit -m "feat(runtime): add v1 active source subset"
```

### Task 3: Update docs and artifact validation

**Files:**
- Modify: `scripts/validate_artifacts.py`
- Modify: `README.md`

**Step 1: Write the failing test**

Add a test or verification assertion that the new runtime artifact is included in artifact validation and that the runtime-first subset is documented.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.runtime.test_source_scope -v`
Expected: FAIL because docs/validation expectations are not yet reflected.

**Step 3: Write minimal implementation**

Update:
- artifact validation script to include `artifacts/runtime/v1_active_sources.yaml`
- README to state that v1 runtime validation targets the active subset first

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.runtime.test_source_scope -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/validate_artifacts.py README.md tests/agent/runtime/test_source_scope.py
git commit -m "docs(runtime): document v1 active source subset"
```

### Task 4: Full verification and progress logging

**Files:**
- Modify: `claude-progress.txt`

**Step 1: Update progress log**

Append the active-source-subset summary, verification commands, and next step to `claude-progress.txt`.

**Step 2: Run verification**

Run:
- `python -m unittest tests.agent.runtime.test_source_scope -v`
- `python scripts/validate_artifacts.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `python -m compileall -q apps tests scripts evals`

Expected:
- source-scope tests PASS
- artifact validation PASS
- full suite PASS
- compile check PASS

**Step 3: Commit**

```bash
git add claude-progress.txt
git commit -m "docs: log active source subset progress"
```

