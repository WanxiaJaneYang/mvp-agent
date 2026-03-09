# M004 Postprocess Design

## Goal

Add the missing deterministic postprocess layer for citation validation so unrecoverable validation failures turn into explicit abstain output instead of stopping at a `retry` status with no delivery-ready artifact.

## Scope

This slice covers:
- abstain-output generation for unrecoverable validation failures
- preserving partial output when validation degradation is acceptable
- a small postprocess helper that turns stage-8 validation results into delivery-ready synthesis payloads
- tests for `ok`, `partial`, and `abstained` paths

This slice does not cover:
- retrieval scoring changes
- email or HTML delivery rendering
- full orchestrator integration of a second validation retry cycle

## Why This Slice

The repo now has:
- ingestion and retrieval primitives
- core citation validation logic
- stage-8 validation status generation

What is still missing is the deterministic contract for what happens after validation cannot recover. Without that, downstream delivery code has no stable artifact shape for abstentions.

## Approaches Considered

### Option A: Small synthesis postprocess helper

Add a helper that takes validation output and returns:
- unchanged synthesis for `ok`
- degraded synthesis for `partial`
- explicit abstain synthesis for unrecoverable retry/failure cases

Why this is preferred:
- narrowest missing runtime piece
- testable without full orchestration
- preserves future freedom for delivery integration

### Option B: Fold abstain logic into stage8 directly

Make stage8 return abstain payloads itself.

Why this is not preferred:
- mixes validation and post-validation output shaping
- makes later retry orchestration less clear

### Option C: Delay abstain logic until delivery modules exist

Why this is not preferred:
- leaves the trust-critical runtime gap open
- forces downstream modules to infer missing behavior

## Selected Design

### Module Layout

- `apps/agent/synthesis/postprocess.py`
  - `finalize_validation_outcome(...)`
  - `build_abstain_synthesis(...)`

### Output Rules

- `ok`:
  - keep synthesis unchanged
  - return final status `ok`
- `partial`:
  - keep validator-degraded synthesis
  - return final status `partial`
- unrecoverable validation failure:
  - return final status `abstained`
  - emit explicit abstain bullets in each core section
  - carry reason metadata forward for delivery/logging

### Abstain Payload Shape

Each core section gets one bullet with explicit insufficient-evidence text. Non-core metadata may be preserved when useful, but the core evidence-bearing sections must be deterministic and unambiguous.

### Testing Strategy

Tests will cover:
- `ok` passthrough
- `partial` passthrough
- abstain synthesis generation from a retry/failure outcome
- deterministic abstain metadata and section coverage
