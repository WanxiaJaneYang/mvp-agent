# Issue 214 Source Ops Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the shared source control plane and operator dashboard flow for `#214` without making the dashboard the source of truth for runtime source behavior.

**Architecture:** Keep source contract file-based, add a separate control-plane SQLite store for operator state and strategies, and expose a dynamic resolved-source service that runtime, workers, and dashboard can all consume. Land the data model and lifecycle services first, then add dashboard views and content visibility on top of those shared interfaces.

**Tech Stack:** Python, FastAPI, SQLite, YAML source registry loading, existing `repo_dashboard` static frontend, `unittest`.

---

### Task 1: Add Shared Control-Plane Storage Foundations (`#215`)

**Files:**
- Create: `apps/agent/storage/source_control_plane.py`
- Modify: `apps/agent/pipeline/types.py`
- Modify: `artifacts/modelling/data_model.md`
- Test: `tests/agent/storage/test_source_control_plane.py`

**Step 1: Write the failing test**

Create `tests/agent/storage/test_source_control_plane.py` with focused storage expectations:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from apps.agent.storage.source_control_plane import (
    control_plane_db_path,
    ensure_control_plane_db,
    SourceControlPlaneStore,
)


class SourceControlPlaneStoreTests(unittest.TestCase):
    def test_bootstraps_control_plane_tables(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            db_path = ensure_control_plane_db(base_dir=base_dir)
            self.assertEqual(db_path, control_plane_db_path(base_dir=base_dir))

            store = SourceControlPlaneStore(base_dir=base_dir)
            operator_state = store.get_operator_state("reuters_business")

            self.assertIsNone(operator_state)
            self.assertTrue(db_path.exists())
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.storage.test_source_control_plane -v`

Expected: FAIL with import error because `apps.agent.storage.source_control_plane` does not exist yet.

**Step 3: Write minimal implementation**

Create `apps/agent/storage/source_control_plane.py` with:

- `control_plane_db_path(base_dir: Path) -> Path`
- `ensure_control_plane_db(base_dir: Path) -> Path`
- `SourceControlPlaneStore`
- schema initialization for:
  - `source_operator_state`
  - `source_strategy_versions`
  - `source_onboarding_runs`

Add typed rows to `apps/agent/pipeline/types.py`, for example:

```python
class SourceOperatorStateRow(TypedDict):
    source_id: str
    is_active: int
    strategy_state: str
    current_strategy_id: str | None
```

Update `artifacts/modelling/data_model.md` with the additive control-plane schema so runtime code is not the only source of truth for the new persistence contract.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.storage.test_source_control_plane -v`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/storage/source_control_plane.py apps/agent/pipeline/types.py artifacts/modelling/data_model.md tests/agent/storage/test_source_control_plane.py
git commit -m "feat: add source control plane storage foundation"
```

### Task 2: Add Control-Plane CRUD And Lifecycle Persistence (`#215`)

**Files:**
- Modify: `apps/agent/storage/source_control_plane.py`
- Modify: `tests/agent/storage/test_source_control_plane.py`

**Step 1: Write the failing test**

Extend `tests/agent/storage/test_source_control_plane.py` with lifecycle persistence checks:

```python
def test_persists_operator_state_strategy_versions_and_onboarding_runs(self) -> None:
    with TemporaryDirectory() as tmpdir:
        store = SourceControlPlaneStore(base_dir=Path(tmpdir))
        store.upsert_operator_state(
            {
                "source_id": "reuters_business",
                "is_active": 1,
                "strategy_state": "missing",
                "current_strategy_id": None,
                "latest_strategy_id": None,
                "last_onboarding_run_id": None,
                "last_collection_status": "idle",
                "last_collection_started_at": None,
                "last_collection_finished_at": None,
                "last_collection_error": None,
                "activated_at": "2026-04-04T00:00:00Z",
                "deactivated_at": None,
                "updated_at": "2026-04-04T00:00:00Z",
            }
        )
        state = store.get_operator_state("reuters_business")
        self.assertEqual(state["strategy_state"], "missing")
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.storage.test_source_control_plane -v`

Expected: FAIL because CRUD methods like `upsert_operator_state(...)` do not exist yet.

**Step 3: Write minimal implementation**

Add storage methods:

- `get_operator_state(source_id)`
- `list_operator_states()`
- `upsert_operator_state(row)`
- `insert_strategy_version(row)`
- `list_strategy_versions(source_id)`
- `insert_onboarding_run(row)`
- `update_onboarding_run(run_id, ...)`
- `list_onboarding_runs(source_id)`

Keep timestamps and status transitions explicit. Do not add dashboard-only columns.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.storage.test_source_control_plane -v`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/storage/source_control_plane.py tests/agent/storage/test_source_control_plane.py
git commit -m "feat: add source control plane lifecycle persistence"
```

### Task 3: Add Resolved Source Service And Runtime Eligibility (`#216`)

**Files:**
- Create: `apps/agent/runtime/resolved_sources.py`
- Modify: `apps/agent/runtime/source_scope.py`
- Modify: `apps/agent/pipeline/types.py`
- Test: `tests/agent/runtime/test_resolved_sources.py`

**Step 1: Write the failing test**

Create `tests/agent/runtime/test_resolved_sources.py` to cover merged source resolution:

```python
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.agent.runtime.resolved_sources import load_resolved_sources
from apps.agent.storage.source_control_plane import SourceControlPlaneStore


class ResolvedSourcesTests(unittest.TestCase):
    def test_marks_only_active_ready_sources_as_runtime_eligible(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            store = SourceControlPlaneStore(base_dir=base_dir)
            # seed operator state + approved strategy here
            resolved = load_resolved_sources(base_dir=base_dir)
            eligible = [item for item in resolved if item["runtime_eligible"]]
            self.assertEqual([item["source_id"] for item in eligible], ["reuters_business"])
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.runtime.test_resolved_sources -v`

Expected: FAIL with import error because `apps.agent.runtime.resolved_sources` does not exist yet.

**Step 3: Write minimal implementation**

Create `apps/agent/runtime/resolved_sources.py` with:

- `load_resolved_sources(...)`
- `get_resolved_source(source_id, ...)`
- helper to compute `runtime_eligible`

Update `apps/agent/pipeline/types.py` with a `ResolvedSource` typed shape.

Keep the join dynamic:

```python
runtime_eligible = (
    bool(operator_state["is_active"])
    and operator_state["strategy_state"] == "ready"
    and operator_state["current_strategy_id"] is not None
    and current_strategy is not None
    and current_strategy["strategy_status"] == "approved"
)
```

Update `apps/agent/runtime/source_scope.py` so the legacy YAML active list can remain as compatibility input while the resolved-source path becomes available for later collection work.

**Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.agent.runtime.test_resolved_sources -v
python -m unittest tests.agent.runtime.test_source_scope -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/runtime/resolved_sources.py apps/agent/runtime/source_scope.py apps/agent/pipeline/types.py tests/agent/runtime/test_resolved_sources.py
git commit -m "feat: add resolved source service and runtime eligibility"
```

### Task 4: Add Onboarding Queue And Strategy Approval Services (`#217`, `#218`)

**Files:**
- Create: `tools/repo_dashboard/services/source_ops_service.py`
- Modify: `apps/agent/storage/source_control_plane.py`
- Test: `tests/tools/test_repo_dashboard_services.py`

**Step 1: Write the failing test**

Extend `tests/tools/test_repo_dashboard_services.py` with service-level lifecycle checks:

```python
def test_enqueue_onboarding_and_approve_strategy_updates_source_lifecycle(self) -> None:
    service = SourceOpsService(repo_root=repo_root, data_dir=data_dir)
    service.set_source_active("reuters_business", True)
    run = service.enqueue_onboarding("reuters_business")
    service.record_proposed_strategy(run["onboarding_run_id"], proposed_strategy_row)
    service.approve_strategy("reuters_business", proposed_strategy_row["strategy_id"])
    resolved = service.get_resolved_source("reuters_business")
    self.assertEqual(resolved["strategy_state"], "ready")
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.tools.test_repo_dashboard_services -v`

Expected: FAIL because `SourceOpsService` and onboarding/approval methods do not exist yet.

**Step 3: Write minimal implementation**

Create `tools/repo_dashboard/services/source_ops_service.py` as a thin orchestration layer over the shared control plane.

Add methods:

- `list_resolved_sources()`
- `get_resolved_source(source_id)`
- `set_source_active(source_id, is_active)`
- `enqueue_onboarding(source_id)`
- `record_proposed_strategy(onboarding_run_id, row)`
- `approve_strategy(source_id, strategy_id)`

Keep onboarding asynchronous in model only: record the job and status, but do not execute the worker in-process.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.tools.test_repo_dashboard_services -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tools/repo_dashboard/services/source_ops_service.py apps/agent/storage/source_control_plane.py tests/tools/test_repo_dashboard_services.py
git commit -m "feat: add source onboarding and approval services"
```

### Task 5: Add Dashboard Sources API And Views (`#219`)

**Files:**
- Modify: `tools/repo_dashboard/app.py`
- Modify: `tools/repo_dashboard/static/index.html`
- Modify: `tools/repo_dashboard/static/app.js`
- Modify: `tools/repo_dashboard/static/styles.css`
- Test: `tests/tools/test_repo_dashboard_api.py`
- Test: `tests/tools/test_repo_dashboard_frontend.py`

**Step 1: Write the failing test**

Add API and frontend expectations:

```python
def test_sources_endpoints_return_resolved_source_rows(self) -> None:
    response = client.get("/api/sources")
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()["items"][0]["source_id"], "reuters_business")

def test_root_serves_sources_panel_shell(self) -> None:
    response = client.get("/")
    self.assertIn('id="sources-panel"', response.text)
    self.assertIn('id="source-detail-panel"', response.text)
```

**Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.tools.test_repo_dashboard_api -v
python -m unittest tests.tools.test_repo_dashboard_frontend -v
```

Expected: FAIL because the new API routes and HTML anchors do not exist yet.

**Step 3: Write minimal implementation**

Add new FastAPI routes in `tools/repo_dashboard/app.py`:

- `GET /api/sources`
- `GET /api/sources/{source_id}`
- `POST /api/sources/{source_id}/activate`
- `POST /api/sources/{source_id}/deactivate`
- `POST /api/sources/{source_id}/onboarding`
- `POST /api/sources/{source_id}/strategies/{strategy_id}/approve`

Update frontend files to render:

- a `Sources` overview panel
- a source detail panel
- read-only strategy summary

Keep contract display read-only and keep current runtime run panels intact.

**Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.tools.test_repo_dashboard_api -v
python -m unittest tests.tools.test_repo_dashboard_frontend -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/repo_dashboard/app.py tools/repo_dashboard/static/index.html tools/repo_dashboard/static/app.js tools/repo_dashboard/static/styles.css tests/tools/test_repo_dashboard_api.py tests/tools/test_repo_dashboard_frontend.py
git commit -m "feat: add source ops dashboard views and actions"
```

### Task 6: Add Documents And Probe-Sample Visibility (`#220`)

**Files:**
- Create: `tools/repo_dashboard/services/source_content_service.py`
- Modify: `tools/repo_dashboard/app.py`
- Modify: `tools/repo_dashboard/static/app.js`
- Modify: `tools/repo_dashboard/static/styles.css`
- Test: `tests/tools/test_repo_dashboard_api.py`

**Step 1: Write the failing test**

Extend the dashboard API test with document and probe-sample detail expectations:

```python
def test_source_detail_returns_documents_and_probe_samples_separately(self) -> None:
    response = client.get("/api/sources/reuters_business")
    payload = response.json()
    self.assertIn("documents", payload)
    self.assertIn("probe_samples", payload)
    self.assertNotEqual(payload["documents"], payload["probe_samples"])
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.tools.test_repo_dashboard_api -v`

Expected: FAIL because source detail does not yet include content-plane query results.

**Step 3: Write minimal implementation**

Create `tools/repo_dashboard/services/source_content_service.py` with query methods:

- `list_source_documents(source_id, limit=...)`
- `list_source_probe_samples(source_id, limit=...)`
- `count_source_documents(source_id)`

Initial implementation may read official documents from the current runtime store and return an empty probe-sample list until onboarding sample persistence lands, but the API shape must already keep the two planes separate.

Update source detail endpoint and frontend tabs so `Fetched Documents` and `Probe Samples` are distinct UI surfaces.

**Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest tests.tools.test_repo_dashboard_api -v
python -m unittest tests.tools.test_repo_dashboard_frontend -v
python -m unittest tests.tools.test_repo_dashboard_services -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/repo_dashboard/services/source_content_service.py tools/repo_dashboard/app.py tools/repo_dashboard/static/app.js tools/repo_dashboard/static/styles.css tests/tools/test_repo_dashboard_api.py
git commit -m "feat: add source document and probe sample visibility"
```

### Final Verification

Run the focused verification set after Task 6:

```bash
python -m unittest tests.agent.storage.test_source_control_plane tests.agent.runtime.test_resolved_sources tests.agent.runtime.test_source_scope tests.tools.test_repo_dashboard_services tests.tools.test_repo_dashboard_api tests.tools.test_repo_dashboard_frontend -v
python -m compileall -q apps tests tools scripts
python scripts/validate_artifacts.py
python scripts/validate_decision_record_schema.py
```

Expected:

- all targeted tests pass
- compile step is clean
- artifact validators remain green

### Notes For Execution

- keep `source_registry.yaml` file-based and read-only from dashboard code
- do not make onboarding worker execution in-process
- do not treat `artifacts/runtime/v1_active_sources.yaml` as the mutable source-of-truth once control-plane eligibility exists
- keep probe samples out of official document queries even if probe-sample persistence is initially thin
