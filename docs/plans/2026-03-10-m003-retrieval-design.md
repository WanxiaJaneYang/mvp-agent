# M003 Retrieval Design

## Goal

Create the first executable chunking and FTS indexing skeleton so normalized documents can become retrieval units for downstream evidence-pack work.

## Scope

This slice covers:
- chunk splitting for full-text documents
- stable `chunk_index` ordering
- `chunks`-compatible row generation
- `chunks_fts`-compatible row generation
- deterministic in-memory keyword lookup for tests
- hard-fail behavior when invalid chunk/index rows are produced

This slice does not cover:
- SQLite writes
- BM25 or full FTS5 behavior
- reranking, diversity constraints, or evidence-pack assembly
- embeddings or vector indexing

## Why This Slice

The repo now has:
- orchestration contracts
- ingestion/extraction/normalization/dedup primitives
- budget guard preflight and ledger helpers

The next P0 dependency is transforming normalized documents into retrieval units. A pure-Python chunking/indexing skeleton lands that contract without binding the repo to a database layer too early.

## Approaches Considered

### Option A: Pure-Python row builders plus in-memory keyword search

Implement deterministic helpers that:
- split text into chunks
- build `chunks` and `chunks_fts` row dictionaries
- provide a minimal keyword search helper for test verification

Why this is preferred:
- smallest shippable slice
- easy to test without SQLite fixtures
- keeps future storage integration straightforward

### Option B: Direct SQLite + FTS5 implementation now

Add actual SQLite table creation and insert/query logic in the first slice.

Why this is not preferred:
- couples the slice to DB lifecycle and migration details
- adds test setup noise before retrieval contracts are stable

### Option C: Chunker only, defer index row builders

Implement chunk splitting and stop there.

Why this is not preferred:
- leaves the main acceptance criterion half-finished
- still blocks downstream retrieval work from testing against index-shaped data

## Selected Design

### Module Layout

- `apps/agent/retrieval/chunker.py`
  - chunk splitting for normalized document records
  - metadata-only and empty-body skip behavior
- `apps/agent/retrieval/fts_index.py`
  - `chunks` row builder
  - `chunks_fts` row builder
  - simple in-memory keyword search helper for tests

### Data Flow

1. take a normalized document record
2. skip chunking when `metadata_only = 1` or `body_text` is empty
3. split text into ordered spans with stable boundaries
4. emit `chunks` rows with:
   - `chunk_id`
   - `doc_id`
   - `chunk_index`
   - `text`
   - `token_count`
   - `char_start`
   - `char_end`
   - `created_at`
5. emit matching `chunks_fts` rows with:
   - `text`
   - `doc_id`
   - `chunk_id`
   - `publisher`
   - `source_id`
   - `published_at`

### Failure Rules

- invalid chunk rows must raise immediately
- invalid FTS rows must raise immediately
- metadata-only documents produce no chunk/index rows and do not raise

### Testing Strategy

Tests will cover:
- stable chunk ordering
- metadata-only documents skipped
- `chunks` row shape
- `chunks_fts` row shape
- keyword lookup returning the most relevant rows
- hard failure when invalid chunk/index rows are passed into the row builder
