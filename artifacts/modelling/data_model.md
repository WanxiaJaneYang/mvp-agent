# Data Model v1 (SQLite + FTS5)

Purpose: Define the local-first SQLite schema for ingestion, retrieval, citation validation, synthesis outputs, alerts, and run/budget tracking.

Status: Modelling deliverable B (data_model.md)

## 1. Design Goals

- Enforce evidence-grounded outputs (no uncited factual claims).
- Support incremental ingestion with deduplication.
- Support hybrid retrieval (FTS5 now, vector-ready schema).
- Preserve claim-to-citation traceability for validator checks.
- Keep runtime controls observable (runs, budgets, errors).

## 2. ID and Time Conventions

- IDs are app-generated text IDs with stable prefixes:
- `src_<uuid>`, `doc_<uuid>`, `chunk_<uuid>`, `cite_<uuid>`, `pack_<uuid>`, `syn_<uuid>`, `alert_<uuid>`, `run_<uuid>`.
- `uuid` should use UUIDv7 where available (ordered by time); fallback UUIDv4.
- All timestamps are UTC ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`).
- Report scheduling uses user timezone (Asia/Singapore), stored in config; persisted timestamps remain UTC.

## 3. SQLite Pragmas and Extensions

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA cache_size = -20000;
```

Use SQLite FTS5 for keyword retrieval.

## 4. Core Tables (DDL)

### 4.1 Sources

```sql
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY, -- matches source_registry.yaml id
  name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('rss', 'html', 'pdf', 'api')),
  credibility_tier INTEGER NOT NULL CHECK (credibility_tier BETWEEN 1 AND 4),
  paywall_policy TEXT NOT NULL CHECK (paywall_policy IN ('full', 'metadata_only')),
  fetch_interval TEXT NOT NULL,
  tags_json TEXT NOT NULL, -- JSON array
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0,1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

### 4.2 Documents

```sql
CREATE TABLE IF NOT EXISTS documents (
  doc_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  publisher TEXT NOT NULL,
  canonical_url TEXT NOT NULL,
  title TEXT,
  author TEXT,
  language TEXT,
  doc_type TEXT, -- news, policy_statement, minutes, speech, report, commentary, filing
  published_at TEXT,
  fetched_at TEXT NOT NULL,
  paywall_policy TEXT NOT NULL CHECK (paywall_policy IN ('full', 'metadata_only')),
  metadata_only INTEGER NOT NULL CHECK (metadata_only IN (0,1)),
  rss_snippet TEXT, -- allowed for metadata_only sources
  body_text TEXT,   -- NULL when metadata_only = 1
  content_hash TEXT NOT NULL,
  ingestion_run_id TEXT REFERENCES runs(run_id),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'retracted', 'error')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(canonical_url),
  UNIQUE(content_hash)
);
```

### 4.3 Document Tags and Entities

```sql
CREATE TABLE IF NOT EXISTS document_tags (
  doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  tag TEXT NOT NULL,
  confidence REAL,
  PRIMARY KEY (doc_id, tag)
);

CREATE TABLE IF NOT EXISTS document_entities (
  doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  entity TEXT NOT NULL,
  entity_type TEXT NOT NULL, -- ticker, org, country, person, index, commodity
  confidence REAL,
  PRIMARY KEY (doc_id, entity, entity_type)
);
```

### 4.4 Chunks (retrieval units)

```sql
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  token_count INTEGER,
  char_start INTEGER,
  char_end INTEGER,
  embedding_model TEXT,  -- nullable in v1
  embedding_vector BLOB, -- nullable in v1; reserved for vector index integration
  created_at TEXT NOT NULL,
  UNIQUE(doc_id, chunk_index)
);
```

### 4.5 Evidence Packs

```sql
CREATE TABLE IF NOT EXISTS evidence_packs (
  pack_id TEXT PRIMARY KEY,
  purpose TEXT NOT NULL CHECK (purpose IN ('daily_brief', 'alert')),
  query_text TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  unique_publishers INTEGER NOT NULL,
  tier_1_pct REAL NOT NULL,
  tier_2_pct REAL NOT NULL,
  tier_3_pct REAL NOT NULL,
  tier_4_pct REAL NOT NULL,
  max_publisher_pct REAL NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_pack_items (
  pack_id TEXT NOT NULL REFERENCES evidence_packs(pack_id) ON DELETE CASCADE,
  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  publisher TEXT NOT NULL,
  credibility_tier INTEGER NOT NULL CHECK (credibility_tier BETWEEN 1 AND 4),
  retrieval_score REAL NOT NULL,
  semantic_score REAL,
  recency_score REAL,
  credibility_score REAL,
  rank_in_pack INTEGER NOT NULL,
  PRIMARY KEY (pack_id, chunk_id)
);
```

### 4.6 Synthesis Outputs (daily brief + alert body)

```sql
CREATE TABLE IF NOT EXISTS syntheses (
  synthesis_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('daily_brief', 'alert')),
  run_id TEXT REFERENCES runs(run_id),
  pack_id TEXT REFERENCES evidence_packs(pack_id),
  scheduled_for_local_date TEXT, -- YYYY-MM-DD in Asia/Singapore
  generated_at TEXT NOT NULL,
  validation_passed INTEGER NOT NULL CHECK (validation_passed IN (0,1)),
  removed_bullets_count INTEGER NOT NULL DEFAULT 0,
  retry_count INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK (status IN ('ok', 'partial', 'abstained', 'failed')),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS synthesis_bullets (
  synthesis_id TEXT NOT NULL REFERENCES syntheses(synthesis_id) ON DELETE CASCADE,
  section TEXT NOT NULL CHECK (section IN ('prevailing', 'counter', 'minority', 'watch', 'changed')),
  bullet_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  claim_span_count INTEGER NOT NULL DEFAULT 1,
  is_abstain INTEGER NOT NULL DEFAULT 0 CHECK (is_abstain IN (0,1)),
  confidence_label TEXT, -- optional: high, medium, low
  PRIMARY KEY (synthesis_id, section, bullet_index)
);
```

### 4.7 Citations (claim/bullet binding)

```sql
CREATE TABLE IF NOT EXISTS citations (
  citation_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  publisher TEXT NOT NULL,
  doc_id TEXT NOT NULL REFERENCES documents(doc_id),
  chunk_id TEXT REFERENCES chunks(chunk_id),
  url TEXT NOT NULL,
  title TEXT,
  published_at TEXT,
  fetched_at TEXT,
  quote_start INTEGER,
  quote_end INTEGER,
  quote_text TEXT,      -- must be NULL if source paywall_policy = metadata_only
  snippet_text TEXT,    -- allowed for all, required fallback for metadata_only
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bullet_citations (
  synthesis_id TEXT NOT NULL,
  section TEXT NOT NULL,
  bullet_index INTEGER NOT NULL,
  claim_span_index INTEGER NOT NULL DEFAULT 0,
  citation_id TEXT NOT NULL REFERENCES citations(citation_id) ON DELETE CASCADE,
  PRIMARY KEY (synthesis_id, section, bullet_index, claim_span_index, citation_id),
  FOREIGN KEY (synthesis_id, section, bullet_index)
    REFERENCES synthesis_bullets(synthesis_id, section, bullet_index)
    ON DELETE CASCADE
);
```

### 4.8 Alerts (rate-limit and delivery state)

```sql
CREATE TABLE IF NOT EXISTS alerts (
  alert_id TEXT PRIMARY KEY,
  synthesis_id TEXT NOT NULL REFERENCES syntheses(synthesis_id),
  category TEXT NOT NULL CHECK (category IN ('policy', 'macro_release', 'corporate_event', 'narrative_shift')),
  score_total REAL NOT NULL,
  score_importance REAL NOT NULL,
  score_evidence REAL NOT NULL,
  score_confidence REAL NOT NULL,
  score_relevance REAL NOT NULL,
  score_noise_risk REAL NOT NULL,
  triggered_at TEXT NOT NULL,
  delivered_email_at TEXT,
  delivered_local_page_at TEXT,
  suppressed_reason TEXT,
  created_at TEXT NOT NULL
);
```

### 4.9 Portfolio and Relevance

```sql
CREATE TABLE IF NOT EXISTS portfolio_positions (
  position_id TEXT PRIMARY KEY,
  ticker TEXT NOT NULL,
  weight_pct REAL NOT NULL CHECK (weight_pct >= 0 AND weight_pct <= 100),
  asset_type TEXT DEFAULT 'equity',
  notes TEXT, -- optional manual mapping hints (themes, sectors, macro sensitivities)
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(ticker)
);

CREATE TABLE IF NOT EXISTS relevance_flags (
  relevance_id TEXT PRIMARY KEY,
  synthesis_id TEXT NOT NULL REFERENCES syntheses(synthesis_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  relevance_score REAL NOT NULL,
  risk_flag TEXT NOT NULL, -- deterministic categories such as direct_holding or mapped_theme
  rationale TEXT,
  created_at TEXT NOT NULL
);
```

- `portfolio_positions.notes` stores optional user-supplied mapping hints for local-first relevance matching.
- `relevance_flags` capture deterministic relevance/risk context for a synthesis and must not encode buy/sell guidance.

### 4.10 Runs, Budget, and Failures

```sql
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  run_type TEXT NOT NULL CHECK (run_type IN ('ingestion', 'daily_brief', 'alert_scan', 'alert_dispatch', 'maintenance')),
  started_at TEXT NOT NULL,
  ended_at TEXT,
  status TEXT NOT NULL CHECK (status IN ('running', 'ok', 'failed', 'stopped_budget', 'partial')),
  docs_fetched INTEGER NOT NULL DEFAULT 0,
  docs_ingested INTEGER NOT NULL DEFAULT 0,
  chunks_indexed INTEGER NOT NULL DEFAULT 0,
  tool_calls INTEGER NOT NULL DEFAULT 0,
  pages_fetched INTEGER NOT NULL DEFAULT 0,
  model_input_tokens INTEGER NOT NULL DEFAULT 0,
  model_output_tokens INTEGER NOT NULL DEFAULT 0,
  estimated_cost_usd REAL NOT NULL DEFAULT 0,
  error_summary TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS budget_ledger (
  ledger_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(run_id),
  recorded_at TEXT NOT NULL,
  window_type TEXT NOT NULL CHECK (window_type IN ('hourly', 'daily', 'monthly')),
  window_start TEXT NOT NULL,
  window_end TEXT NOT NULL,
  cost_usd REAL NOT NULL,
  cap_usd REAL NOT NULL,
  exceeded INTEGER NOT NULL CHECK (exceeded IN (0,1))
);
```

## 5. Index Plan

```sql
CREATE INDEX IF NOT EXISTS idx_documents_source_published ON documents(source_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_publisher_published ON documents(publisher, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_fetched_at ON documents(fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_pack_items_pack_rank ON evidence_pack_items(pack_id, rank_in_pack);
CREATE INDEX IF NOT EXISTS idx_pack_items_source ON evidence_pack_items(source_id, credibility_tier);

CREATE INDEX IF NOT EXISTS idx_citations_doc ON citations(doc_id);
CREATE INDEX IF NOT EXISTS idx_citations_source_published ON citations(source_id, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_triggered_at ON alerts(triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_category ON alerts(category);

CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_budget_window ON budget_ledger(window_type, window_start DESC);
```

## 6. FTS5 Plan (Keyword Retrieval)

Use content-linked FTS5 to query chunk text efficiently:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  text,
  doc_id UNINDEXED,
  chunk_id UNINDEXED,
  publisher UNINDEXED,
  source_id UNINDEXED,
  published_at UNINDEXED,
  tokenize = 'porter unicode61'
);
```

FTS sync strategy:

- On chunk insert: insert into `chunks_fts`.
- On chunk update: delete old row, insert new row.
- On chunk delete: delete corresponding `chunks_fts` row.

Recommended query pattern:

1. Retrieve top `N` by BM25 from `chunks_fts`.
2. Join `chunks`, `documents`, `sources`.
3. Re-rank with recency + credibility weighting.
4. Apply diversity caps before forming `evidence_packs`.

## 7. Constraints Mapped to Requirements

- Citation contract: `synthesis_bullets` + `bullet_citations` + `citations`.
- Paywall compliance: `documents.metadata_only`, `citations.quote_text` nullable; no quote for metadata-only sources.
- Publisher diversity: `evidence_pack_items.publisher` and stored diversity stats in `evidence_packs`.
- Daily/alert rate limits: `alerts.triggered_at` + app logic with cooldown and daily cap.
- Budget hard-stop: `runs.status = stopped_budget` + `budget_ledger.exceeded = 1`.

## 8. Validation Queries (Smoke Checks)

```sql
-- 1) Any bullet without citations?
SELECT sb.synthesis_id, sb.section, sb.bullet_index
FROM synthesis_bullets sb
LEFT JOIN bullet_citations bc
  ON bc.synthesis_id = sb.synthesis_id
 AND bc.section = sb.section
 AND bc.bullet_index = sb.bullet_index
WHERE bc.citation_id IS NULL;

-- 2) Paywall violation (metadata-only source with quote_text)
SELECT c.citation_id, c.source_id
FROM citations c
JOIN sources s ON s.source_id = c.source_id
WHERE s.paywall_policy = 'metadata_only'
  AND c.quote_text IS NOT NULL;

-- 3) Dominance violation in evidence packs (>40% one publisher)
SELECT pack_id, publisher, COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY pack_id) AS publisher_pct
FROM evidence_pack_items
GROUP BY pack_id, publisher
HAVING publisher_pct > 0.40;
```

## 9. Migration and Evolution Notes

- Keep schema additive in v1; avoid destructive migrations.
- Vector search can be introduced with an external index (FAISS/Qdrant/SQLite extension) keyed by `chunk_id`.
- If multi-user support is added later, introduce `user_id` across portfolio, runs, syntheses, and alerts.

