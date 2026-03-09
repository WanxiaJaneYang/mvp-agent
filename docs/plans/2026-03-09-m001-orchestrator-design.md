# M001 Orchestrator Design

## Goal

Define the first executable runtime skeleton for `M001` so the repository has a shared orchestration contract for future ingestion, retrieval, synthesis, and delivery stages.

## Scope

This slice covers:
- shared run and stage types
- a reusable stage execution contract
- a minimal orchestrator entry point
- bounded retry handling
- lifecycle recording aligned to the `runs` table contract

This slice does not cover:
- SQLite persistence
- ingestion logic
- retrieval logic
- synthesis generation
- delivery integrations

## Constraints

- Keep the implementation local-first and small.
- Align run statuses and fields with `artifacts/modelling/data_model.md`.
- Do not introduce uncontrolled loops.
- Keep budget hard-stop behavior compatible with the existing budget guard module.

## Approaches Considered

### Option A: Minimal executable orchestrator with injected recorder

Add shared runtime types, a stage protocol, and an orchestrator that emits lifecycle snapshots through an injected recorder callable.

Why this is preferred:
- satisfies the acceptance criteria for run types and bounded retries
- keeps storage concerns decoupled while the runtime is still forming
- gives downstream tickets a stable execution contract

### Option B: Orchestrator plus direct SQLite write path

Implement the same orchestration layer, but write directly to SQLite-shaped `runs` rows now.

Why this is not preferred:
- forces storage design before the repo has DB setup code
- expands the slice beyond the smallest useful step
- makes tests heavier and more brittle

### Option C: Docs-only specification update

Refine modelling docs without adding executable runtime code.

Why this is not preferred:
- does not reduce the current implementation gap
- leaves downstream P0 tasks blocked on missing runtime primitives

## Selected Design

### Architecture

- `apps/agent/pipeline/types.py`
  - `RunType`
  - `RunStatus`
  - `RunCounters`
  - `RunContext`
  - `StageResult`
- `apps/agent/pipeline/stages.py`
  - stage protocol / callable contract
  - retry classification helper
- `apps/agent/orchestrator.py`
  - orchestrator entry point
  - per-run lifecycle handling
  - bounded stage retries

### Lifecycle Model

The orchestrator will:
1. validate the requested run type
2. create a `RunContext` with timestamps and zeroed counters
3. emit a `running` lifecycle snapshot
4. execute stages in order
5. retry only retryable failures up to a configured cap
6. emit a final lifecycle snapshot with `ok`, `partial`, `failed`, or `stopped_budget`

### Recorder Contract

The orchestrator will accept an injected lifecycle recorder. The recorder receives a plain dictionary aligned with the `runs` table model:
- `run_id`
- `run_type`
- `started_at`
- `ended_at`
- `status`
- `docs_fetched`
- `docs_ingested`
- `chunks_indexed`
- `tool_calls`
- `pages_fetched`
- `model_input_tokens`
- `model_output_tokens`
- `estimated_cost_usd`
- `error_summary`
- `created_at`

This keeps the execution contract stable while deferring actual SQLite integration.

### Error Handling

- Retryable stage failures are retried up to a fixed cap.
- Non-retryable failures fail the run immediately.
- Budget-stop signals map to `stopped_budget`.
- Partial outcomes can be surfaced explicitly when a stage returns partial status without hard failure.
- No background loops or open-ended retries are allowed.

### Testing Strategy

Tests will cover:
- supported run-type dispatch
- invalid run-type rejection
- lifecycle recorder snapshots
- bounded retry success path
- bounded retry exhaustion path
- budget-stop propagation

Tests will use an in-memory recorder and simple fake stages.
