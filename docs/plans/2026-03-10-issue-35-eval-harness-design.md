# Issue #35 Eval Harness Design

## Goal

Extend the existing eval harness so it catches regressions in retrieval ordering and abstain/postprocess behavior, not just citation validation.

## Scope

This slice covers:
- extending `evals/run_eval_suite.py` with additional case dispatch
- adding `retrieval` golden cases for evidence-pack ordering and pack-size bounds
- adding `postprocess` golden cases for deterministic abstain handling
- documenting the new case types and a follow-on TODO for chained end-to-end evals

This slice does not cover:
- delivery evals
- alert evals
- chained retrieval -> validation -> abstain execution in a single case
- CI workflow restructuring

## Why This Slice

The repo already has:
- citation validation runtime and golden evals
- retrieval ranking/runtime helpers
- deterministic abstain/postprocess behavior

The missing piece is regression coverage across those newer contracts. Extending the existing harness is the smallest change that makes that coverage real.

## Approaches Considered

### Option A: Extend the existing golden-case runner

Add new `type` values and case evaluators inside `evals/run_eval_suite.py`.

Why this is preferred:
- reuses the current harness shape
- stays fast and deterministic
- minimizes review surface

### Option B: Add more citation-only cases

Why this is not preferred:
- does not measure retrieval or abstain behavior
- leaves the most recent runtime slices uncovered

### Option C: Build a mini end-to-end eval runner now

Why this is not preferred:
- too wide for the first increment
- mixes multiple contracts and makes failures harder to localize

## Selected Design

### Runner Changes

Extend `evals/run_eval_suite.py` to support:
- `citation`
- `retrieval`
- `postprocess`

Each case type gets:
- a dedicated runner helper
- a common failure-collection pattern

### Golden Case Shapes

#### `retrieval`
- inputs:
  - `query_text`
  - `pack_size`
  - `fts_rows`
- expected:
  - ordered `chunk_id` list
  - expected pack length

#### `postprocess`
- inputs:
  - `validation_result`
- expected:
  - final `status`
  - `abstain_reason` when relevant
  - optional per-section checks on the synthesized abstain output

### Documentation

Update `evals/README.md` to:
- describe each supported case type
- note the local command to run the suite
- add an explicit TODO for future chained retrieval -> validation -> abstain eval cases

### Testing Strategy

Use TDD against the eval runner itself:
- write failing tests for dispatch and failure reporting
- add minimal golden fixtures that exercise the new case types
- verify the runner stays compatible with the existing citation cases

