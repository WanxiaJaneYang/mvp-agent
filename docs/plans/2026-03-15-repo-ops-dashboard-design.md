# Issue #180 Repo Ops Dashboard Design

## Goal

Add a local-only Repo Ops Dashboard that lets an operator inspect the repo's architecture and runtime health, launch the key daily-brief commands, and review the latest publish decision plus artifacts from one page.

## Scope

This slice covers:
- a FastAPI backend under `tools/repo_dashboard/`
- a single static HTML/CSS/vanilla JS dashboard
- local command execution for fixture, eval, targeted-test, and live runs
- structured run metadata persisted to a dashboard-owned JSON store
- artifact discovery for generated HTML briefs and decision records
- diagram surfacing from existing modelling docs and any repo image assets already present
- local launch docs with one-command startup

This slice does not cover:
- hosted deployment
- auth or multi-user access
- replacing existing pipeline scripts
- changing daily-brief runtime contracts or decision-record schema

## Why This Slice

The repo already contains the operational pieces the dashboard needs:
- runnable local scripts for fixture and live daily-brief flows
- a deterministic eval harness
- a targeted unittest command for daily-brief delivery/citation validation
- generated runtime artifacts such as `brief.html`, decision records, and run summaries
- modelling docs that describe architecture, data model, and pipeline flow

What is missing is a thin operator layer that organizes these assets without changing the underlying runtime.

## Approaches Considered

### Option A: FastAPI server with static HTML and a JSON-backed local state store

Use FastAPI for API routes and static-file serving, keep the UI in plain HTML/CSS/JS, run commands through a narrow subprocess service, and persist dashboard-owned state in `tools/repo_dashboard/data/`.

Why this is preferred:
- matches the user's requested stack
- keeps dependencies minimal
- is easy to run locally with one command
- preserves a strong boundary between dashboard metadata and existing runtime artifacts

### Option B: Pure static page that shells out through ad hoc local scripts

Serve a file-based dashboard and rely on separate scripts to write status files the UI reads.

Why this is not preferred:
- cannot trigger runs safely from the page without adding a backend anyway
- makes log polling and in-progress state awkward
- spreads orchestration logic across more files

### Option C: Full SPA toolchain with React/Vite

Build a richer local app with a bundler and component framework.

Why this is not preferred:
- violates the user's minimal-dependency constraint
- adds build tooling that the repo does not otherwise need
- is unnecessary for a single operator page

## Selected Design

### Architecture

Add a self-contained dashboard package:

```text
tools/repo_dashboard/
  app.py
  README.md
  services/
    artifact_reader.py
    command_runner.py
    repo_scan.py
    status_store.py
  static/
    index.html
    app.js
    styles.css
  data/
    dashboard_state.json
    runs/
```

The backend owns:
- command definitions and safe execution
- run metadata and current log snapshots
- diagram/artifact discovery
- a lightweight overview model derived from repo files

The frontend owns:
- rendering the single dashboard page
- polling the API for state and logs
- launching runs through button actions
- surfacing informative hold/abstain states instead of treating them as generic failures

### Data and Status Model

Keep dashboard metadata separate from pipeline outputs.

`dashboard_state.json` should store:
- latest known health entries for each run type
- the currently active run, if any
- recent run summaries with timestamps, status, exit code, command, and artifact paths
- a cached overview payload so the page can load fast even before a manual refresh

Each run in `data/runs/<run_id>.json` should include:
- `run_id`
- `run_kind` (`fixture`, `evals`, `targeted_tests`, `live`)
- `command`
- `started_at_utc`
- `finished_at_utc`
- `status` (`queued`, `running`, `ok`, `partial`, `failed`)
- `exit_code`
- `log_path`
- `base_dir`
- `artifact_paths`
- `publish_decision`
- `reason`
- `reason_codes`
- `summary`

The dashboard should treat:
- `publish` as a positive outcome
- `hold` as an informative outcome that still exposes reasons and artifacts
- abstained/partial pipeline runs as valid runtime states, not hidden errors

### Command Execution

Support exactly these commands:
- `python scripts/run_daily_brief_fixture.py --base-dir .tmp_repo_dashboard/demo`
- `python evals/run_eval_suite.py`
- `python -m unittest tests.agent.daily_brief.test_runner tests.agent.delivery.test_html_report tests.agent.validators.test_citation_validator -v`
- `python scripts/run_daily_brief.py --base-dir .tmp_repo_dashboard/live`

Design constraints:
- only one dashboard-triggered run executes at a time
- logs stream to a run-specific log file under `tools/repo_dashboard/data/runs/`
- the backend exposes the latest log tail through polling
- completion triggers artifact discovery plus a state write

### Artifact and Diagram Discovery

The dashboard should prefer existing repo outputs instead of generating new diagrams.

For diagrams:
- first look for existing SVG/PNG assets under repo docs/artifacts
- otherwise derive linkable diagram cards from modelling docs such as:
  - `artifacts/modelling/pipeline.md`
  - `artifacts/modelling/data_model.md`
  - `artifacts/modelling/decision_record_schema.md`

For runtime artifacts:
- inspect the dashboard base dirs `.tmp_repo_dashboard/demo` and `.tmp_repo_dashboard/live`
- inspect standard repo artifact locations such as:
  - `artifacts/runtime/daily_brief_runs/`
  - `artifacts/decision_records/`
- prefer latest `brief.html`, `run_summary.json`, and decision-record JSON paths

### API Shape

Expose these routes:
- `GET /api/overview`
- `GET /api/health`
- `GET /api/latest-run`
- `GET /api/runs`
- `GET /api/artifacts`
- `GET /api/logs/latest`
- `POST /api/run/fixture`
- `POST /api/run/evals`
- `POST /api/run/targeted-tests`
- `POST /api/run/live`
- `POST /api/refresh`

Behavior notes:
- `GET /api/overview` returns diagram/document links plus command definitions
- `GET /api/health` returns the latest health card for each supported run type
- `GET /api/latest-run` returns the active run if one exists, otherwise the most recent completed run
- `GET /api/runs` returns recent run records from the dashboard store
- `GET /api/artifacts` returns latest artifact links grouped by demo/live/latest
- `GET /api/logs/latest` returns the tail of the active or most recent run log
- run POST routes enqueue or start a run and return the created run record
- `POST /api/refresh` rescans repo docs/artifacts and rewrites the cached overview

### Frontend UX

The page should have five operator-first sections:
- header with repo name, refresh control, and current active run badge
- architecture panel with three diagram/document cards: architecture, data model, run flow
- health panel with four status cards: fixture demo, eval suite, targeted tests, latest live run
- control panel with four run buttons and in-progress state
- runtime panel with latest publish decision, reason, reason codes, artifact links, recent runs, and live log tail

The UI should emphasize:
- readable status labels
- visible `reason_codes`
- direct links to `brief.html` and decision records
- informative hold/abstain presentation

### Testing Strategy

Use TDD for the implementation:
- backend tests for repo scanning, state persistence, artifact discovery, and API responses
- command-runner tests that stub subprocess launching and verify state transitions
- minimal HTML/static integration checks through FastAPI test client

Verification should include:
- targeted new tests for the dashboard package
- compile checks for `tools/`
- the existing repo validation commands that remain relevant after dependency/doc updates

## Planned Child Tracks

Implementation should split into these child issues:
- backend runtime and API slice
- frontend operator UI slice
- docs and launch/verification slice

These tracks should coordinate through the planning doc but keep file ownership as separate as practical.
