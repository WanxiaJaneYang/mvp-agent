# Pipeline v1 (Daily + Alert Runs)

Purpose: define the end-to-end local-first pipeline for ingestion, retrieval, synthesis, validation, and delivery with deterministic failure handling.

Status: Modelling deliverable C (`pipeline.md`).

## 1. Run Types

- `ingestion`: fetch and normalize new source content.
- `daily_brief`: create the daily synthesis report.
- `alert_scan`: score potential major events.
- `alert_dispatch`: enforce alert limits and deliver approved alerts.
- `maintenance`: cleanup, compaction, and integrity checks.

## 2. Hard Limits (must stop the run)

- Budget caps: monthly `100`, daily `3`, hourly `0.10` USD.
- Max new documents/day: `200`.
- Default per-source cap/day: `10` (except approved exceptions like SEC/wires).
- Max evidence pack size: `30` chunks.
- Max alerts/day: `3` and cooldown `60` minutes.
- Max synthesis length: daily ~`1200` words, alert ~`400` words.

When any hard limit is exceeded:
- Set run status to `stopped_budget` or `failed`.
- Persist reason to `runs.error_summary`.
- Do not auto-retry the same run.

## 3. Stage-by-Stage Flow

### Stage 0: Preflight

Inputs:
- `source_registry.yaml`
- current UTC timestamp + local timezone config
- budget ledger windows (hour/day/month)

Actions:
- Validate required config and registry shape.
- Check budget windows before model/tool work.
- Compute run limits for this execution.

Failure handling:
- Missing config/schema mismatch -> fail fast.
- Budget exceeded -> stop before fetch/model calls.

### Stage 1: Fetch

Actions:
- Pull candidate docs from RSS/HTML/PDF sources.
- Enforce per-source and global caps.
- Store fetch metadata and raw payload pointers.

Failure handling:
- Source timeout/network error -> record source-level error, continue other sources.
- Robots/paywall blocking -> keep metadata/snippet only.

### Stage 2: Extract

Actions:
- Parse payload to normalized text blocks.
- Keep paywalled documents as metadata-only.

Failure handling:
- Parser failure -> mark doc status `error`, continue.

### Stage 3: Normalize + Enrich

Actions:
- Standardize metadata (`publisher`, `published_at`, `doc_type`, tags/entities).
- Assign credibility tier from source registry.

Failure handling:
- Missing required metadata -> mark doc `error` and skip chunking.

### Stage 4: Deduplicate

Actions:
- Exact dedup by canonical URL and content hash.
- Skip already-ingested docs.

Failure handling:
- Conflicting IDs/hash collision -> keep earliest, mark duplicate and continue.

### Stage 5: Chunk + Index

Actions:
- Split full-text docs into retrieval chunks.
- Insert into `chunks` and `chunks_fts`.
- Keep embedding fields nullable in v1.

Failure handling:
- FTS write failure -> fail run (index integrity risk).

### Stage 6: Retrieve Evidence Pack

Actions:
- Query top candidates via FTS + reranking inputs.
- Apply recency weighting and credibility weighting.
- Enforce diversity constraints:
  - max 40% one publisher
  - at least 50% Tier 1/2
  - at most 15% Tier 4
- Cap final pack at 30 chunks.

Failure handling:
- Cannot satisfy diversity constraints -> degrade gracefully with abstain-ready path and explicit note.

### Stage 7: Synthesize

Actions:
- Build structured output sections:
  - prevailing
  - counterarguments
  - minority
  - what to watch
  - changed since yesterday (daily brief)
- Keep output within section and word caps.

Failure handling:
- Model/tool timeout -> one retry with same evidence pack.
- Second failure -> output abstaining report.

### Stage 8: Citation Validate

Actions:
- Verify every claim/bullet has >=1 citation mapping.
- Verify paywall policy compliance (no fabricated quote spans for `metadata_only`).
- Remove invalid bullets or replace with explicit "insufficient evidence".

Failure handling:
- <=3 removals: deliver with `partial` status.
- >3 removals or empty critical sections: retry once.
- Retry failure: mark synthesis `abstained` and deliver minimal abstain output.

### Stage 9: Alert Scoring + Policy Gate

Actions:
- Score candidates using `alert_scoring.md` formula.
- Enforce cooldown and daily cap.
- Bundle below-threshold but notable events into next daily brief.

Failure handling:
- If policy gate fails (cooldown/daily cap), suppress alert and log reason.

### Stage 10: Deliver + Persist

Actions:
- Write daily HTML output locally.
- Send email for daily brief and approved alerts.
- Store run metrics, costs, and output lineage.
- Persist `decision_record` JSON at `artifacts/decision_records/<YYYY-MM-DD>/<run_id>.json`.
- Include decision rationale, claim/citation coverage, rejected alternatives, risk flags, and guardrail/budget snapshots.

Failure handling:
- Email send error -> keep local deliverable, queue retry in next run.
- Local write error -> fail run and retain logs.

## 4. Incremental Run Logic

- Use `published_at` + `fetched_at` watermarks per source.
- Re-ingest only unseen/updated docs since last successful watermark.
- On partial run failure, persist source-level checkpoints already completed.
- Never reprocess full corpus unless manually requested.

## 5. Retry Policy

- Fetch/extract/source-level operations: continue on per-source errors.
- Synthesis generation: max 1 retry.
- Citation validation: max 1 synthesis retry when critical failures occur.
- No infinite retries; all retries are deterministic and bounded.

## 6. Observability Requirements

Each run must persist:
- `run_id`, run type, start/end times, status.
- Docs fetched/ingested, chunks indexed.
- Token and cost counters.
- Budget window checks and exceed flags.
- Error summary and stage of failure.

## 7. Acceptance Checks for This Pipeline Spec

- Stages cover fetch -> extract -> normalize -> chunk -> index -> retrieve -> synthesize -> validate -> deliver.
- Failure handling is explicit at stage and run levels.
- Incremental run behavior is defined.
- Hard limits and budget stop conditions are explicit.
