# Repo Ops Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local FastAPI-powered Repo Ops Dashboard that exposes architecture context, runtime health, command controls, logs, and artifact links for this repository.

**Architecture:** Keep the dashboard isolated under `tools/repo_dashboard/`, with a typed Python backend that scans repo state and runs existing commands, plus a static single-page UI that polls JSON endpoints. Persist dashboard-specific run metadata in local JSON files without changing the existing pipeline artifact contracts.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, `subprocess`, `json`, `pathlib`, `unittest`, plain HTML/CSS/vanilla JS

---

### Task 1: Land backend scaffolding and dashboard state services

**Issue:** Child issue for backend runtime and API foundations

**Files:**
- Modify: `pyproject.toml`
- Create: `tools/repo_dashboard/app.py`
- Create: `tools/repo_dashboard/services/status_store.py`
- Create: `tools/repo_dashboard/services/repo_scan.py`
- Create: `tools/repo_dashboard/services/artifact_reader.py`
- Create: `tools/repo_dashboard/data/dashboard_state.json`
- Create: `tools/repo_dashboard/data/runs/.gitkeep`
- Create: `tests/tools/test_repo_dashboard_services.py`

**Step 1: Write the failing test**

Add tests covering:
- dashboard state initialization when JSON files do not yet exist
- overview scanning for modelling docs and command definitions
- artifact discovery returning latest decision record and HTML brief when present

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.tools.test_repo_dashboard_services -v`
Expected: FAIL because the dashboard modules do not exist yet.

**Step 3: Write minimal implementation**

Implement:
- a typed local JSON state store
- repo overview scanning for architecture/data model/run flow documents
- artifact readers for daily-brief HTML and decision-record locations
- FastAPI app skeleton with `GET /api/overview`, `GET /api/health`, `GET /api/latest-run`, `GET /api/runs`, `GET /api/artifacts`, and `POST /api/refresh`

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.tools.test_repo_dashboard_services -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml tools/repo_dashboard tests/tools/test_repo_dashboard_services.py
git commit -m "feat(dashboard): add repo dashboard backend scaffolding"
```

### Task 2: Add command runner, run endpoints, and log polling state

**Issue:** Same backend child issue or a follow-up backend sub-issue if needed

**Files:**
- Modify: `tools/repo_dashboard/app.py`
- Create: `tools/repo_dashboard/services/command_runner.py`
- Modify: `tools/repo_dashboard/services/status_store.py`
- Modify: `tests/tools/test_repo_dashboard_services.py`
- Create: `tests/tools/test_repo_dashboard_api.py`

**Step 1: Write the failing test**

Add tests asserting:
- run endpoints create dashboard run records
- only one run can be active at a time
- latest-log polling returns the active run log tail
- completed runs persist publish decision, reason, and reason codes when discoverable from artifacts

**Step 2: Run test to verify it fails**

Run:
- `python -m unittest tests.tools.test_repo_dashboard_services -v`
- `python -m unittest tests.tools.test_repo_dashboard_api -v`

Expected: FAIL because command execution and run endpoints are incomplete.

**Step 3: Write minimal implementation**

Implement:
- safe command definitions for fixture, evals, targeted tests, and live runs
- subprocess execution with per-run log files
- run lifecycle state updates (`queued`, `running`, `ok`, `partial`, `failed`)
- `GET /api/logs/latest`
- `POST /api/run/fixture`
- `POST /api/run/evals`
- `POST /api/run/targeted-tests`
- `POST /api/run/live`

**Step 4: Run test to verify it passes**

Run:
- `python -m unittest tests.tools.test_repo_dashboard_services -v`
- `python -m unittest tests.tools.test_repo_dashboard_api -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tools/repo_dashboard tests/tools/test_repo_dashboard_api.py tests/tools/test_repo_dashboard_services.py
git commit -m "feat(dashboard): add local run orchestration and logs"
```

### Task 3: Build the operator UI against the API contract

**Issue:** Child issue for frontend/operator UI

**Files:**
- Create: `tools/repo_dashboard/static/index.html`
- Create: `tools/repo_dashboard/static/app.js`
- Create: `tools/repo_dashboard/static/styles.css`
- Modify: `tools/repo_dashboard/app.py`
- Create: `tests/tools/test_repo_dashboard_frontend.py`

**Step 1: Write the failing test**

Add tests asserting:
- the FastAPI app serves the dashboard HTML
- the page includes sections for diagrams, health, controls, latest decision, artifacts, and logs
- the static assets are mounted and retrievable

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.tools.test_repo_dashboard_frontend -v`
Expected: FAIL because the static dashboard does not exist yet.

**Step 3: Write minimal implementation**

Implement:
- single-page operator layout
- health cards for fixture/evals/targeted/live
- control buttons wired to the run endpoints
- polling for health/latest-run/logs/artifacts
- clear presentation of `publish_decision`, `reason`, and `reason_codes`
- direct links to latest `brief.html` and decision-record artifacts

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.tools.test_repo_dashboard_frontend -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/repo_dashboard/static tools/repo_dashboard/app.py tests/tools/test_repo_dashboard_frontend.py
git commit -m "feat(dashboard): add operator dashboard ui"
```

### Task 4: Add launch docs, README updates, and end-to-end verification

**Issue:** Child issue for docs/verification/launch

**Files:**
- Create: `tools/repo_dashboard/README.md`
- Modify: `README.md`
- Modify: `tests/agent/test_project_tooling.py`
- Modify: `tests/tools/test_repo_dashboard_frontend.py`

**Step 1: Write the failing test**

Add assertions that:
- the main README documents the dashboard launch command
- the dashboard README includes exact one-command startup instructions

**Step 2: Run test to verify it fails**

Run:
- `python -m unittest tests.agent.test_project_tooling -v`
- `python -m unittest tests.tools.test_repo_dashboard_frontend -v`

Expected: FAIL because the launch documentation is missing.

**Step 3: Write minimal implementation**

Document:
- dependency install/update command
- exact local launch command
- dashboard run buttons and the commands they trigger
- where state/logs/artifacts are stored

**Step 4: Run verification**

Run:
- `python -m unittest tests.tools.test_repo_dashboard_services -v`
- `python -m unittest tests.tools.test_repo_dashboard_api -v`
- `python -m unittest tests.tools.test_repo_dashboard_frontend -v`
- `python scripts/validate_artifacts.py`
- `python scripts/validate_decision_record_schema.py`
- `python -m compileall -q apps tests scripts tools`
- `python -m unittest discover -s tests -t . -p "test_*.py" -v`

Expected:
- dashboard tests PASS
- repo validators PASS
- compile check PASS
- full suite PASS

**Step 5: Commit**

```bash
git add tools/repo_dashboard/README.md README.md tests/agent/test_project_tooling.py
git commit -m "docs(dashboard): add local launch instructions"
```

## Planned Execution Tracks

- Track A: backend runtime and API foundations
- Track B: operator UI and static frontend
- Track C: docs, launch workflow, and final verification

Track A owns the Python services and API contract.
Track B owns `tools/repo_dashboard/static/` plus only the backend changes required to mount or expose static content.
Track C owns README/docs/test updates after the API and UI are in place.
