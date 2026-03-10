# Issue #33 V1 Active Source Subset Design

## Goal

Define and enforce a small US-first source subset for v1 runtime validation so downstream work can build and debug against a stable, intentionally narrow source surface.

## Scope

This slice covers:
- a runtime-readable artifact containing the v1 active source IDs
- a helper that resolves the active subset against the full modelling registry
- tests that validate subset integrity and intended source mix
- documentation describing the subset and its purpose

This slice does not cover:
- changing the full source catalog into an active/inactive matrix
- network fetch implementation
- dynamic source enable/disable configuration
- broader international runtime scope

## Why This Slice

The repository has a strong full modelling registry, but the runtime path does not yet have a narrow source scope. A small explicit subset lowers debugging cost while preserving the full catalog for future phases.

## Approaches Considered

### Option A: Separate runtime allowlist artifact plus resolver helper

Store the full registry unchanged and add a small artifact listing the v1 active source IDs. Runtime helpers resolve those IDs against the full registry when needed.

Why this is preferred:
- smallest runtime-usable step
- avoids overloading the full registry with short-term scope flags
- easy to test and reuse later

### Option B: Mark active/inactive directly inside `source_registry.yaml`

Why this is not preferred:
- mixes permanent catalogue modelling with temporary runtime rollout scope
- creates more drift pressure when the subset changes

### Option C: Docs-only subset description

Why this is not preferred:
- gives no executable source-of-truth to downstream code
- forces later branches to re-encode the same decision

## Selected Design

### Artifact Layout

- `artifacts/runtime/v1_active_sources.yaml`
  - contains the explicit list of active source IDs
  - includes brief rationale and intended v1 properties

### Runtime Helper

- `apps/agent/runtime/source_scope.py`
  - load the full modelling registry
  - load the v1 allowlist
  - return the resolved active source records in stable order
  - fail clearly if the allowlist references a missing source

### Tests

- `tests/agent/runtime/test_source_scope.py`
  - resolves the configured active subset
  - preserves the declared order
  - fails when an allowlist entry is missing from the full registry
  - asserts the subset contains:
    - official US policy/macro sources
    - one full-text secondary source
    - one metadata-only source

### Initial US-First Subset

- `fed_press_releases`
- `us_bls_news`
- `us_bea_news`
- `reuters_business`
- `wsj_markets`

### Documentation

Update:
- `README.md` or a small runtime-facing doc reference to clarify that v1 runtime work targets the active subset first
- artifact validation so the new YAML file is checked

### Error Handling

- missing artifact file -> explicit `FileNotFoundError`
- malformed YAML -> validation failure via existing artifact validation flow
- unknown source ID in allowlist -> explicit `ValueError`

