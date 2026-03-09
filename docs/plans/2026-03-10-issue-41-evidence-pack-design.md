# Issue #41 Evidence-Pack Retrieval Design

## Goal

Build the next retrieval runtime slice after chunking and FTS indexing: a deterministic helper that converts indexed chunk candidates into evidence-pack-item-compatible rows for downstream synthesis.

## Scope

This slice covers:
- deterministic ranking over FTS-shaped rows
- retrieval score composition from keyword, recency, and credibility inputs
- bounded pack-size enforcement
- evidence-pack-item-compatible output rows with stable ranking
- focused unit tests for ordering and size caps

This slice does not cover:
- semantic/vector retrieval
- full diversity enforcement by publisher or tier quotas
- SQLite persistence for `evidence_packs` or `evidence_pack_items`
- synthesis or delivery wiring

## Why This Slice

The repository already implements:
- ingestion primitives
- document chunking
- FTS-shaped indexing rows
- citation validation and abstain postprocess

The next concrete runtime gap is Stage 6 evidence retrieval. A deterministic helper closes that contract gap without prematurely expanding into the whole daily-brief vertical slice.

## Approaches Considered

### Option A: Deterministic in-memory evidence-pack builder

Take FTS-shaped rows plus source metadata, compute a retrieval score, sort, and emit bounded pack rows.

Why this is preferred:
- smallest useful runtime step
- directly addresses issue `#41`
- easy to test locally without database or network dependencies

### Option B: Full Stage 6 retrieval implementation now

Add pack assembly plus diversity constraints and future synthesis hooks.

Why this is not preferred:
- expands scope into multiple modelling concerns at once
- makes the first retrieval MR harder to review and stabilize

### Option C: Extend `search_fts_rows()` only

Add more fields to the existing search helper and stop there.

Why this is not preferred:
- leaves no explicit evidence-pack contract
- pushes ranking and row shaping complexity into the wrong module boundary

## Selected Design

### Module Layout

- `apps/agent/retrieval/evidence_pack.py`
  - build scored evidence candidates from FTS-shaped rows
  - normalize recency and credibility inputs
  - sort and truncate to the requested pack size
  - emit evidence-pack-item-compatible dictionaries

- `tests/agent/retrieval/test_evidence_pack.py`
  - relevance ordering test
  - pack-size cap test
  - stable tie-break ordering test

### Input Contract

The helper will operate on rows that already contain:
- `chunk_id`
- `doc_id`
- `text`
- `source_id`
- `publisher`
- `published_at`
- `credibility_tier`

This keeps the module downstream of current FTS row generation while extending the row shape only as much as retrieval now requires.

### Scoring

The first slice uses a deterministic composite score:

`retrieval_score = keyword_score * 0.5 + recency_score * 0.3 + credibility_score * 0.2`

Where:
- `keyword_score` comes from exact token frequency over query terms
- `recency_score` prefers newer rows based on `published_at`
- `credibility_score` maps tiers as:
  - Tier 1 -> `1.0`
  - Tier 2 -> `0.8`
  - Tier 3 -> `0.6`
  - Tier 4 -> `0.3`

### Output Contract

Each output row will match the `evidence_pack_items` contract shape needed later:
- `chunk_id`
- `source_id`
- `publisher`
- `credibility_tier`
- `retrieval_score`
- `semantic_score` set to `None`
- `recency_score`
- `credibility_score`
- `rank_in_pack`

### Ordering Rules

- sort by descending `retrieval_score`
- break ties by descending `published_at`
- break remaining ties by ascending `chunk_id`

This keeps output deterministic for tests and future reviewers.

### Error Handling

- invalid or missing required row fields should raise `ValueError`
- missing `published_at` should be treated as the oldest possible item
- invalid credibility tiers should raise `ValueError`

### Testing Strategy

Tests will verify:
- stronger keyword match outranks weaker match when other factors are comparable
- newer, more credible rows can outrank older, weaker rows when text relevance is similar
- the final pack is capped at the requested size
- tie-breaks remain stable and deterministic

