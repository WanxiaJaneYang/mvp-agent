# Pipeline v2 (Daily Brief + Alert Runs)

Purpose: define the end-to-end local-first pipeline for ingestion, retrieval, issue planning, claim composition, validation, and delivery with deterministic failure handling.

Status: Modelling deliverable C (`pipeline.md`).

## 1. Run Types

- `ingestion`: fetch and normalize new source content
- `daily_brief`: create the daily issue-centered literature review
- `alert_scan`: score potential major events
- `alert_dispatch`: enforce alert limits and deliver approved alerts
- `maintenance`: cleanup, compaction, and integrity checks

## 2. Hard Limits (must stop the run)

- Budget caps: monthly `100`, daily `3`, hourly `0.10` USD
- Max new documents/day: `200`
- Default per-source cap/day: `10` (except approved exceptions like SEC/wires)
- Max evidence pack size: `30` chunks
- Max alerts/day: `3` and cooldown `60` minutes
- Max daily brief length: about `1200` words
- Max alert length: about `400` words

When any hard limit is exceeded:
- set run status to `stopped_budget` or `failed`
- persist reason to `runs.error_summary`
- do not auto-retry the same run

## 3. Stage-by-Stage Flow

### Stage 0: Preflight

Inputs:
- `source_registry.yaml`
- current UTC timestamp + local timezone config
- budget ledger windows (hour/day/month)

Actions:
- validate required config and registry shape
- check budget windows before model/tool work
- compute run limits for this execution

Failure handling:
- missing config/schema mismatch -> fail fast
- budget exceeded -> stop before fetch/model calls

### Stage 1: Fetch

Actions:
- pull candidate docs from RSS/HTML/PDF sources
- enforce per-source and global caps
- store fetch metadata and raw payload pointers

Failure handling:
- source timeout/network error -> record source-level error, continue other sources
- robots/paywall blocking -> keep metadata/snippet only

### Stage 2: Extract

Actions:
- parse payload to normalized text blocks
- keep paywalled documents as metadata-only

Failure handling:
- parser failure -> mark doc status `error`, continue

### Stage 3: Normalize + Enrich

Actions:
- standardize metadata (`publisher`, `published_at`, `doc_type`, tags/entities)
- assign credibility tier from source registry

Failure handling:
- missing required metadata -> mark doc `error` and skip chunking

### Stage 4: Deduplicate

Actions:
- exact dedup by canonical URL and content hash
- skip already-ingested docs

Failure handling:
- conflicting IDs/hash collision -> keep earliest, mark duplicate and continue

### Stage 5: Chunk + Index

Actions:
- split full-text docs into retrieval chunks
- insert into `chunks` and `chunks_fts`
- keep embedding fields nullable until semantic search is enabled

Failure handling:
- FTS write failure -> fail run (index integrity risk)

### Stage 6: Build Deterministic Evidence Layer

Actions:
- retrieve top candidates via FTS + reranking inputs
- apply recency weighting and credibility weighting
- enforce diversity constraints:
  - max 40% one publisher
  - at least 50% Tier 1/2
  - at most 15% Tier 4
- cap final evidence pack at 30 chunks
- build citation store for all evidence candidates
- load prior brief context for novelty comparisons

Outputs:
- `evidence_pack`
- `citation_store`
- `prior_brief_context`

Failure handling:
- cannot satisfy diversity constraints -> degrade gracefully with abstain-ready path and explicit note

### Stage 7: Issue Planning (Model Layer)

Actions:
- call provider-agnostic issue planner with bounded `evidence_pack` and optional `prior_brief_context`
- require schema-valid JSON output only
- identify 2-3 important issues when evidence supports them
- assign support/opposition/minority/watch evidence groups per issue

Outputs:
- `issue_map.json`

Failure handling:
- timeout or invalid JSON -> retry once with same inputs
- second failure -> brief-level abstain

### Stage 8: Claim Composition (Model Layer)

Actions:
- call provider-agnostic claim composer with `issue_map`, `citation_store`, and `prior_brief_context`
- require schema-valid JSON output only
- produce structured claims for `prevailing`, `counter`, `minority`, and `watch`
- include `why_it_matters`, `confidence`, and `novelty_vs_prior_brief`

Outputs:
- `claim_objects.json`

Failure handling:
- timeout or invalid JSON -> retry once with same inputs
- second failure -> brief-level abstain

### Stage 9: Validation + Critic

Actions:
- run deterministic citation validation
- run paywall-policy validation
- run numeric/date/source-quality checks
- verify issue consistency:
  - claims under one issue share the same `issue_id`
  - `prevailing`, `counter`, and `minority` address the same issue question
- optionally run critic pass to detect shallow source-by-source paraphrase

Failure handling:
- minor claim failures -> drop invalid claims and continue with partial issue output
- critical issue failures -> retry claim composer once
- second critical failure -> issue-level or brief-level abstain

### Stage 10: Deliver + Persist

Actions:
- render local HTML output from structured issues and claims
- send email for daily brief and approved alerts
- store run metrics, costs, and output lineage
- persist:
  - `issue_map`
  - `claim_objects`
  - validator report
  - critic report
  - final HTML artifact
  - `decision_record` artifact under `artifacts/decision_records/<YYYY-MM-DD>/<run_id>.json`
- validate the `decision_record` schema before writing to disk

Failure handling:
- email send error -> keep local deliverable, queue retry in next run
- local write error -> fail run and retain logs

## 4. Incremental Run Logic

- use `published_at` + `fetched_at` watermarks per source
- re-ingest only unseen/updated docs since last successful watermark
- on partial run failure, persist source-level checkpoints already completed
- never reprocess full corpus unless manually requested

## 5. Retry Policy

- fetch/extract/source-level operations: continue on per-source errors
- issue planner: max 1 retry
- claim composer: max 1 retry
- validation-triggered composer retry: max 1 additional composer retry
- no infinite retries; all retries are deterministic and bounded

## 6. Abstain Policy

- **Issue-level abstain:** one issue can abstain if evidence is insufficient while other issues still deliver
- **Brief-level abstain:** if no trustworthy issues remain after validation, deliver abstaining report
- abstain output must explain why evidence was insufficient and list what evidence was available

## 7. Observability Requirements

Each run must persist:
- `run_id`, run type, start/end times, status
- docs fetched/ingested, chunks indexed
- evidence pack diversity stats
- token and cost counters by model stage
- budget window checks and exceed flags
- validator/critic outcomes
- error summary and stage of failure

## 8. Acceptance Checks for This Pipeline Spec

- stages cover fetch -> extract -> normalize -> chunk -> index -> evidence build -> issue planning -> claim composition -> validate -> deliver
- failure handling is explicit at stage and run levels
- incremental run behavior is defined
- hard limits and budget stop conditions are explicit
- daily brief architecture is issue-centered rather than one-query / one-bucket synthesis
