# Issue 214 Source Ops Dashboard Design

**Goal**

Define the shared source control plane needed for `#214` so source activation, onboarding, strategy approval, and fetched-document visibility become first-class runtime concepts rather than dashboard-local state.

**Scope**

This design covers:

- repo-level source control-plane tables and lifecycle semantics
- resolved-source service boundaries shared by runtime, agent workers, and dashboard
- the operator surface to view sources, activate/deactivate them, run onboarding, approve strategies, and inspect fetched documents
- alignment with `#210`, `#209`, and `#213`

This design does not turn the dashboard into the source of truth for source contracts, and it does not redesign the content store in this issue.

## Why This Exists

The current repo has:

- a reviewed source list in [artifacts/modelling/source_registry.yaml](/D:/aiProjects/workspaces/mvp-agent/.worktrees/issue-214-source-ops-dashboard/artifacts/modelling/source_registry.yaml)
- an active-subset artifact in `artifacts/runtime/v1_active_sources.yaml`
- direct type-based runtime source resolution in [apps/agent/runtime/source_scope.py](/D:/aiProjects/workspaces/mvp-agent/.worktrees/issue-214-source-ops-dashboard/apps/agent/runtime/source_scope.py)
- dashboard-local JSON state in [tools/repo_dashboard/services/status_store.py](/D:/aiProjects/workspaces/mvp-agent/.worktrees/issue-214-source-ops-dashboard/tools/repo_dashboard/services/status_store.py)

That is not enough for the new operating model.

The intended direction is:

`source contract -> operator state -> approved strategy -> resolved source view -> collection worker`

The dashboard is only the operator surface for that model. It must not invent a second private state model.

## Design Constraints

- `#210` remains the reviewed source-contract layer. Contract stays file-based.
- `#209` should later consume the same resolved source view to drive fetch/storage coverage work.
- `#213` should own storage abstractions. `#214` must depend on those interfaces instead of hard-coding content storage details.
- Daily ingest remains source-driven, not freeform web research.
- A source does not enter steady-state collection until it has an approved strategy.
- Dashboard state must not be stored in mutable YAML files.

## Architecture

The design separates three planes.

### 1. Contract Plane

Reviewed source definitions remain file-based:

- source identity
- source metadata
- source contract fields from `#210`

This is still owned by `source_registry.yaml` and review-driven changes.

### 2. Control Plane

A new shared control-plane SQLite database stores runtime and operator state:

- activation state
- strategy lifecycle
- onboarding job lifecycle
- current approved strategy pointer

This database is repo-level shared infrastructure, not dashboard-local storage.

### 3. Content Plane

Documents, probe samples, and chunks remain content-plane concerns:

- `documents` are official ingest outputs
- `probe samples` are onboarding/exploration outputs
- `chunks` remain downstream retrieval material

`#214` only depends on content-plane query abstractions. It must not lock the repo into SQLite for content storage. The long-term direction may move content-plane storage toward a document-oriented backend, but that migration is out of scope here.

## Shared Control-Plane Schema

The new tables exist to be consumed by runtime, workers, and future issues first. The dashboard only reads and mutates them through services.

### `source_operator_state`

One row per `source_id`. Stores current operational state.

Required fields:

- `source_id` primary key
- `is_active`
- `strategy_state = missing | proposed | ready | paused`
- `current_strategy_id` nullable
- `latest_strategy_id` nullable
- `last_onboarding_run_id` nullable
- `last_collection_status = idle | queued | running | succeeded | failed`
- `last_collection_started_at` nullable
- `last_collection_finished_at` nullable
- `last_collection_error` nullable
- `activated_at` nullable
- `deactivated_at` nullable
- `updated_at`

Semantics:

- runtime eligibility depends on `is_active = true` and `strategy_state = ready`
- `current_strategy_id` is the strategy runtime should execute
- `latest_strategy_id` may point at a newer `proposed` strategy than the current approved one

### `source_strategy_versions`

One row per strategy version. Stores source-specific executable collection strategy.

Required fields:

- `strategy_id` primary key
- `source_id`
- `version`
- `strategy_status = proposed | approved | superseded | rejected`
- `entrypoint_url`
- `fetch_via`
- `content_mode`
- `parser_profile` nullable
- `max_items_per_run`
- `strategy_summary_json`
- `strategy_details_json`
- `created_from_run_id`
- `created_at`
- `approved_at` nullable

Semantics:

- strategy is stored in a hybrid model
- stable, frequently-consumed fields are first-class columns
- richer strategy details remain in JSON
- runtime executes only the current approved strategy
- historical strategies remain queryable for inspection and rollback decisions

### `source_onboarding_runs`

One row per asynchronous onboarding job.

Required fields:

- `onboarding_run_id` primary key
- `source_id`
- `status = queued | running | succeeded | failed`
- `worker_kind`
- `worker_ref` nullable
- `submitted_at`
- `started_at` nullable
- `finished_at` nullable
- `proposed_strategy_id` nullable
- `error_message` nullable
- `result_summary_json` nullable

Semantics:

- job lifecycle is tracked independently from strategy lifecycle
- a successful onboarding run may emit a `proposed_strategy_id`
- failed onboarding does not mutate the current approved strategy

## Resolved Source View

The repo should not materialize a second source-of-truth table. Instead, runtime and dashboard should consume a service-level resolved view built from:

- file-based source contract
- `source_operator_state`
- current approved strategy from `source_strategy_versions`

This resolved view should expose:

- contract fields from `#210`
- current operational state
- latest onboarding status
- approved executable strategy when present
- runtime eligibility flag

It should be computed dynamically through a shared service layer, not persisted as a separate table.

## Source Lifecycle

The first implementation only needs these states:

- `inactive`
- `active + missing`
- `active + proposed`
- `active + ready`

Interpretation:

- `inactive`: not eligible for daily collection
- `active + missing`: operator activated source, but there is no approved strategy
- `active + proposed`: onboarding produced a proposal, but operator has not approved it
- `active + ready`: active source with approved executable strategy; eligible for steady-state collection

`paused` can exist as a future extension, but should not complicate the first-cut workflow.

## Operator Workflows

### Activate / Deactivate

- operator toggles activation from dashboard
- this updates `source_operator_state`
- activation does not auto-run onboarding
- if no approved strategy exists, activation yields `active + missing`

### Run Onboarding

- operator manually triggers onboarding
- dashboard enqueues an asynchronous job
- worker performs bounded per-source exploration against the source surface
- worker may propose a new strategy version
- successful onboarding transitions the source to `active + proposed`

Onboarding is not broad-web discovery. It is source-bounded strategy discovery so future runs can become deterministic.

### Approve Strategy

- operator reviews the proposed strategy in read-only form
- approval marks that version `approved`
- any previous approved version becomes `superseded`
- `current_strategy_id` is updated
- `strategy_state` becomes `ready`

Only after this step does the source enter steady-state collection.

## Dashboard Surface

The existing `repo_dashboard` should grow an operator-facing `Sources` area.

### Sources List

Each source row should display:

- contract summary: `source_id`, `name`, `fetch_via`, `source_role`, `content_mode`
- current operational state: `is_active`, `strategy_state`, `last_collection_status`
- current strategy version when available
- latest onboarding status
- fetched document count

Actions:

- `Activate`
- `Deactivate`
- `Run onboarding`
- `Approve strategy`
- `View details`

### Source Detail

The detail page remains read-only for contract and strategy content. It should have five sections:

- `Contract`
- `Operator State`
- `Current Strategy`
- `Strategy History / Onboarding Runs`
- `Fetched Documents` and `Probe Samples`

`Fetched Documents` and `Probe Samples` should be separate tabs, not one combined timeline.

## Content-Plane Query Boundary

`#214` should not redefine how content is stored. It only requires stable query interfaces.

Required query capabilities:

- list official fetched documents by `source_id`
- list onboarding probe samples by `source_id`
- provide counts and recent records for dashboard summaries

Rules:

- probe samples must not appear in the official documents view
- official documents must remain the collection outputs used for downstream evidence and citation work
- chunks are not first-class dashboard list items in v1

## Service Interfaces

### Control-Plane Service

Required operations:

- `list_resolved_sources(...)`
- `get_resolved_source(source_id)`
- `set_source_active(source_id, is_active)`
- `enqueue_onboarding(source_id)`
- `list_onboarding_runs(source_id)`
- `list_strategy_versions(source_id)`
- `approve_strategy(source_id, strategy_id)`

### Content-Plane Query Service

Required operations:

- `list_source_documents(source_id, ...)`
- `list_source_probe_samples(source_id, ...)`
- `count_source_documents(source_id)`

The dashboard should call services, not join files, DB tables, and content storage directly.

## Async Execution Model

Onboarding jobs should run outside the dashboard process.

First-cut shape:

- dashboard submits onboarding job request
- job is recorded in `source_onboarding_runs`
- a separate worker/CLI executes the job
- dashboard polls or refreshes for status changes

The dashboard is not the job runner.

## Compatibility With Neighbor Issues

### `#210`

`#214` consumes the source-contract fields but does not edit them in the UI. The reviewed contract remains file-based and PR-driven.

### `#209`

`#209` should later consume the same resolved source view and approved strategies to drive coverage expansion. It should not invent a different active-source state model.

### `#213`

`#213` should own the storage abstractions behind:

- control-plane DB access
- document/sample queries
- future content-plane storage changes

`#214` depends on those interfaces and should not hard-code SQLite layout for content-plane access.

## Testing Scope

Minimum tests for the first implementation:

### Control-Plane Schema and Services

- create/read/update the new control-plane tables
- resolve source state from contract + operator state + current strategy
- verify runtime eligibility logic

### Lifecycle Transitions

- activate without strategy -> `active + missing`
- onboarding success -> `active + proposed`
- approve strategy -> `active + ready`
- deactivate -> source removed from eligible set

### Dashboard API

- list endpoint returns contract summary + operator state + strategy summary
- detail endpoint returns strategy history, onboarding runs, document list, and probe sample list
- approval and onboarding endpoints enforce valid transitions

### Guardrails

- unapproved strategies are not runtime-eligible
- probe samples never appear in official document queries
- dashboard does not mutate reviewed source contract files

## Sub-Issue Shape

This design suggests the following execution slices under `#214`:

1. shared control-plane schema and service foundation
2. resolved-source service and runtime eligibility integration
3. dashboard sources list and source detail views
4. onboarding queue and worker handoff integration
5. strategy approval flow and lifecycle guards
6. fetched-documents and probe-samples content queries

These should be split so the shared data model lands before UI-heavy work.

## Recommended Implementation Order

1. add shared control-plane schema and storage/service access
2. add resolved-source service
3. add runtime eligibility integration on top of resolved sources
4. add dashboard sources list
5. add source detail view
6. add onboarding enqueue flow
7. add strategy approval flow
8. connect official document and probe-sample queries

## Rollout Notes

- keep source contract file-based
- make control-plane changes additive
- keep existing dashboard run-status behavior intact while the source operator surface is added
- do not require a full content-plane migration before landing control-plane work
- allow the dashboard to become an operator surface without making it the owner of core runtime logic
