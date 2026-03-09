# M002 Ingestion Design

## Goal

Create the first executable ingestion skeleton for fetch planning, extraction, normalization, and deduplication so downstream chunking and retrieval work has schema-compatible document inputs.

## Scope

This slice covers:
- source iteration with cap enforcement
- RSS and HTML metadata extraction helpers
- normalized `documents`-compatible record generation
- exact dedup helpers by canonical URL and content hash
- tests for paywall-safe metadata-only handling

This slice does not cover:
- real HTTP fetching
- parser libraries for arbitrary HTML/PDF body extraction
- database writes
- chunking or indexing

## Why This Slice

The repo now has:
- orchestration contracts (`M001`)
- budget-stop preflight observability

The next hard dependency is document creation. A pure-Python ingestion skeleton can land now without introducing network, parser, or DB complexity too early.

## Approaches Considered

### Option A: Pure-Python ingestion primitives with injected payloads

Implement fetch planning, extraction, normalization, and dedup as deterministic helpers operating on provided source definitions and payload dictionaries.

Why this is preferred:
- smallest shippable step
- easy to test locally
- preserves future freedom to swap in real network/parsing layers later

### Option B: Full network fetch implementation now

Add real RSS and HTML fetching in the first slice.

Why this is not preferred:
- expands the slice into I/O, retries, timeouts, and parser fragility
- makes tests slower and less deterministic

### Option C: Docs-only ingestion spec

Refine modelling docs without adding runtime code.

Why this is not preferred:
- does not reduce the implementation gap
- keeps M003 blocked

## Selected Design

### Module Layout

- `apps/agent/ingest/fetch.py`
  - source selection
  - per-source/global cap enforcement
- `apps/agent/ingest/extract.py`
  - RSS payload extraction
  - HTML payload extraction
- `apps/agent/ingest/normalize.py`
  - normalized document record builder
- `apps/agent/ingest/dedup.py`
  - exact dedup by URL and content hash

### Data Flow

1. fetch planner chooses sources and truncates candidate payloads by source and global limits
2. extractor converts raw source payloads into a small intermediate metadata shape
3. normalizer emits `documents`-compatible dictionaries:
   - `source_id`
   - `publisher`
   - `canonical_url`
   - `title`
   - `author`
   - `language`
   - `doc_type`
   - `published_at`
   - `fetched_at`
   - `paywall_policy`
   - `metadata_only`
   - `rss_snippet`
   - `body_text`
   - `content_hash`
   - `status`
4. dedup helpers decide whether a candidate is new or duplicate

### Paywall Rules

- `metadata_only` sources must produce `body_text = None`
- `metadata_only` sources may retain title, snippet, and URL metadata
- `full` sources may emit body text when the extracted payload includes it

### Testing Strategy

Tests will cover:
- source cap enforcement
- global cap enforcement
- RSS extraction shape
- HTML extraction shape
- metadata-only normalization forbidding body text
- dedup by canonical URL
- dedup by content hash
