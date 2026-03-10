# Issue #36 Daily Brief Vertical Slice Design

## Goal

Build the first executable daily-brief vertical slice so one deterministic local command can turn a narrow source subset into a citation-grounded HTML brief plus inspectable intermediate artifacts.

## Scope

This slice covers:
- a deterministic runner for the first `daily_brief` path
- committed fixture payloads for the active US-first source subset
- SQLite-compatible JSON artifact emission for intermediate runtime rows
- a rule-based synthesis builder for the core brief sections
- citation validation and abstain fallback integration
- local HTML brief rendering
- decision-record persistence for the produced output

This slice does not cover:
- live network fetch connectors
- real SQLite writes
- email delivery
- cross-run `changed since yesterday` output
- alert scoring or alert delivery

## Why This Slice

The repository now has isolated building blocks for ingestion, chunking, retrieval, validation, and decision-record persistence, but it still lacks a single runnable path that proves they work together. The first vertical slice should optimize for deterministic inspection and low debugging cost rather than realism, so fixture inputs and JSON row artifacts are the right initial shape.

## Approaches Considered

### Option A: Deterministic runner built from existing stage primitives

Create a narrow daily-brief runner that loads fixture payloads, reuses the current ingest/retrieval/validation helpers, builds a simple rule-based synthesis, renders HTML, and writes decision/output artifacts.

Why this is preferred:
- proves the end-to-end path without adding a second integration surface
- keeps failures reproducible and offline-friendly
- preserves compatibility with the current data model and decision-record contract

### Option B: Demo script outside the runtime path

Why this is not preferred:
- bypasses `run_pipeline`-style lifecycle expectations and output lineage
- increases rewrite risk when the real runtime path is added

### Option C: Full persistence and delivery stack in the first slice

Why this is not preferred:
- widens the issue into SQLite bootstrapping and delivery plumbing
- makes failures harder to localize before the first brief path is proven

## Selected Design

### Runtime Architecture

- Add a dedicated daily-brief runner module that assembles the deterministic path end to end.
- Load the full source registry, then narrow runtime scope through `artifacts/runtime/v1_active_sources.yaml`.
- Read committed fixture payloads keyed by active `source_id`.
- Reuse existing ingest, chunking, retrieval, validation, and decision-record helpers instead of duplicating logic.
- Emit SQLite-compatible JSON artifacts for intermediate rows and one final HTML brief artifact for the user-facing output.

### Data Flow

1. Load active sources from the runtime subset artifact.
2. Load committed fixture payloads for those sources.
3. Plan fetch items with the existing per-source/global cap logic.
4. Extract payloads into the shared intermediate shape.
5. Build normalized document rows, adding the runtime fields current helpers do not yet assign:
   - stable `doc_id`
   - `credibility_tier`
   - any run-linked bookkeeping needed by the artifact set
6. Build chunk rows and FTS rows from full-text documents.
7. Derive a deterministic topic/query from the ingested documents using simple rule-based selection rather than a fixed hard-coded query.
8. Build an evidence pack from the FTS rows.
9. Build one structured synthesis with sections:
   - `prevailing`
   - `counter`
   - `minority`
   - `watch`
10. Construct citation rows so every output bullet has explicit citation IDs.
11. Validate the synthesis and route retry-like outcomes through the abstain postprocess path.
12. Render the validated output to local HTML.
13. Persist a decision record tied to the generated output artifact.

### Artifact Contract

Write inspectable JSON artifacts for the first slice so later SQLite integration can map directly onto the existing data model:

- `sources`
- `documents`
- `chunks`
- `fts_rows`
- `evidence_pack_items`
- `citations`
- `synthesis`
- run summary / counters

Also write:
- a local HTML daily brief under `artifacts/daily/<date>/`
- a schema-valid decision record under `artifacts/decision_records/<date>/`

### Synthesis Strategy

- The first slice uses deterministic rule-based synthesis, not a model call.
- Bullet text is assembled from the top evidence-pack rows and document metadata rather than from canned hard-coded prose.
- The builder should preserve source diversity where available by mapping evidence into:
  - mainstream / official narrative (`prevailing`)
  - alternate or moderating angle (`counter`)
  - lower-weight or supplementary angle (`minority`)
  - forward-looking release or risk indicator (`watch`)
- The `changed` section is intentionally deferred until a prior-run comparison surface exists.

### Error Handling

- Missing fixture data for one active source is a source-level omission, not a hard crash.
- If all active sources are missing fixture data, the run should fail clearly.
- If extraction or normalization fails for one payload, skip that payload and record the omission in run-summary artifacts.
- If no usable chunkable or citeable evidence remains, emit the abstain path and still write HTML plus decision record.
- If HTML rendering or decision-record validation fails, fail the run rather than downgrading silently.

### Testing Strategy

- Add focused unit tests for:
  - fixture loading
  - source scoping
  - deterministic topic/query selection
  - citation row construction
  - HTML rendering
- Add an end-to-end deterministic test that asserts the runner writes:
  - JSON row artifacts
  - HTML output
  - a schema-valid decision record
  - core sections with citations
- Add an abstain-path test where insufficient evidence still yields a valid abstain artifact set.

### Explicit TODOs

- replace fixture inputs with live fetch connectors
- replace JSON row artifacts with real SQLite writes
- add cross-run `changed since yesterday` comparison
- add email delivery on top of local HTML generation
