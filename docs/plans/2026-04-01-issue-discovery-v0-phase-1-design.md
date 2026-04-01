# Phase 1: Issue Discovery v0

Issue anchor: GitHub issue [#193](https://github.com/WanxiaJaneYang/mvp-agent/issues/193)

## Goal

Introduce a first additive `issue_discovery v0` path that improves daily-brief issue selection without forcing a same-phase rewrite of retrieval, rendering, runtime storage, or alert delivery.

Phase 1 should change what the system chooses to talk about, while keeping the existing downstream brief path as intact as possible.

## Scope

Phase 1 covers:

- core object contracts for event and issue discovery
- scoring primitives and selection formula for `daily_brief` issue selection
- additive schema changes
- feature-flagged rollout
- evaluation and rollout plan
- success metrics

Phase 1 does not cover:

- product expansion strategy
- alert-policy redesign
- board/dashboard UX design
- replacing current briefing or rendering contracts
- deleting old `query_text`-based paths

## Phase 1 Consumer

The first consumer for `issue_discovery v0` is `daily_brief`.

Alerts and board/dashboard consumers may later reuse shared event and scoring primitives, but they are not in Phase 1 rollout scope. This avoids forcing alert policy into a daily-brief selection model.

## Core Object Contracts

Each object contract below defines:

- primary key
- upstream inputs
- downstream consumers
- scope

### `canonical_news_item`

Primary key:
- `news_item_id`

Upstream inputs:
- normalized `documents`
- optional representative `chunks`

Downstream consumers:
- `event_cluster`
- `daily_market_snapshot`

Scope:
- persistent
- canonical
- not product-scoped

Phase 1 note:
- this can begin as a lightweight projection over `documents`
- `news_item_id` may alias `doc_id` in Phase 1 if that avoids unnecessary schema churn

### `event_cluster`

Primary key:
- `event_id`

Upstream inputs:
- `canonical_news_item[]`
- representative chunk references for similarity and evidence pointers

Downstream consumers:
- `event_assessment`
- `issue_candidate`
- alerts and board ranking

Scope:
- persistent
- canonical
- not product-scoped

Phase 1 note:
- clustering is document or news-item centric, not chunk centric
- `chunk_id` links may be stored as representative evidence pointers, but they do not define cluster identity

### `event_assessment`

Primary key:
- `(run_id, event_id, profile_id, scoring_version)`

Upstream inputs:
- `event_cluster`
- prior-run or prior-brief context
- scoring configuration

Downstream consumers:
- `daily_market_snapshot`
- `issue_candidate`

Scope:
- run-scoped
- persistent
- not product-scoped

Phase 1 note:
- contextual scores such as novelty, impact, and confidence belong here, not on the canonical `event_cluster`

### `daily_market_snapshot`

Primary key:
- `snapshot_id`

Upstream inputs:
- `event_cluster[]`
- `event_assessment[]`
- lens taxonomy metadata

Downstream consumers:
- scoring inputs
- operator explainability
- issue framing context

Scope:
- run-scoped
- persistent artifact
- not product-scoped

Phase 1 note:
- this is not a canonical cross-run market object
- it is a reproducible run artifact that records how the system saw the day

### `issue_candidate`

Primary key:
- `candidate_id`

Upstream inputs:
- one or more `event_cluster` records
- optional `daily_market_snapshot`
- prior-brief or prior-run delta anchors

Downstream consumers:
- `selector`
- `briefing`
- selection contexts

Scope:
- run-scoped
- persistent
- not product-scoped

Phase 1 note:
- an issue candidate may map to one event or multiple related events
- it must carry run identity and scoring-policy identity

### `selection_context`

Primary key:
- `selection_context_id`

Upstream inputs:
- `issue_candidate[]`
- consumer identity
- selection policy metadata

Downstream consumers:
- `issue_selection`
- product runners

Scope:
- run-scoped
- persistent
- consumer-scoped

Phase 1 note:
- this object exists to avoid baking `daily_brief` assumptions into shared selection tables

### `issue_selection`

Primary key:
- `(selection_context_id, candidate_id)`

Upstream inputs:
- `issue_candidate[]`
- `selection_context`

Downstream consumers:
- `products/daily_brief`

Scope:
- run-scoped
- persistent
- consumer-scoped

Phase 1 note:
- in Phase 1 the only live `consumer_kind` is `daily_brief`
- the table shape should still remain consumer-agnostic

## Scoring Contract

### Range

All scoring primitives in Phase 1 should use a `0.0` to `1.0` range.

Every persisted score should carry:

- the numeric value
- the scoring version
- reason codes explaining why the score landed where it did

### Score Primitives

#### `novelty_score`

- level: event assessment and issue candidate
- meaning: difference versus prior brief or prior run context
- caution: contextual only; do not store as a canonical event field

#### `impact_score`

- level: event assessment and issue candidate
- meaning: expected market transmission breadth and materiality
- alignment: alerts may reuse this primitive, but still keep alert-specific floors

#### `portfolio_relevance_score`

- level: issue candidate
- meaning: relevance to the repo's target retail ETF-holder audience

#### `evidence_strength_score`

- level: issue candidate
- meaning: adequacy of evidence after source-quality, recency, and citation checks

#### `source_convergence_score`

- level: event assessment and issue candidate
- meaning: whether distinct publishers and source roles converge on the same development

Difference from `evidence_strength_score`:
- `evidence_strength_score` asks whether the candidate can support a credible write-up
- `source_convergence_score` asks whether independent source paths are converging on the same underlying event or issue

#### `redundancy_penalty`

- level: issue candidate
- meaning: overlap with already-kept or low-information-gain issue candidates
- alignment: this should be driven by overlap and information-gain gates, not by a second unrelated duplicate detector

### Total Score Formula

Phase 1 initial formula:

`total_score = 0.25*novelty + 0.25*impact + 0.20*portfolio_relevance + 0.15*evidence_strength + 0.15*source_convergence - 0.20*redundancy_penalty`

This is a versioned policy, not a canonical truth.

### Tie-Break Rules

If total scores tie within the configured tolerance:

1. higher `novelty_score`
2. then higher `impact_score`
3. then broader official plus market-media source-role coverage
4. then stronger delta versus prior brief

### Selection Veto Conditions

A candidate should still be dropped even with a high total score when:

- `evidence_strength_score` is below the minimum evidence floor
- the candidate collapses into an already-kept issue under overlap or information-gain gating
- the candidate has no distinct thesis beyond a headline cluster
- the candidate cannot support a substantive counter or watch path

### Reason-Code Alignment

Phase 1 should persist reason codes that map score outcomes to selection behavior, for example:

- `high_novelty`
- `high_market_transmission`
- `high_portfolio_relevance`
- `strong_cross_source_convergence`
- `low_incremental_value`
- `issue_budget_exceeded`
- `below_evidence_floor`
- `headline_cluster_without_thesis`

## Additive Schema

### New Tables

#### `event_clusters`

Canonical fields only:

- `event_id`
- `canonical_title`
- `event_type`
- `first_seen_at`
- `last_seen_at`
- `entity_tags_json`
- `market_tags_json`
- `cluster_version`

#### `event_cluster_items`

- `event_id`
- `news_item_id`
- `doc_id`
- `representative_chunk_id`
- `role_hint`
- `similarity_score`

#### `event_assessments`

- `run_id`
- `event_id`
- `profile_id`
- `scoring_version`
- `novelty_score`
- `impact_score`
- `confidence_score`
- `source_convergence_score`
- `reason_codes_json`

#### `market_snapshots`

- `snapshot_id`
- `run_id`
- `taxonomy_version`
- `profile_id`
- `status`
- `created_at`

#### `market_snapshot_items`

- `snapshot_id`
- `lens`
- `event_ids_json`
- `lens_summary_json`
- `score_inputs_json`
- `operator_notes_json`

#### `issue_candidates`

- `candidate_id`
- `discovery_run_id`
- `profile_id`
- `policy_version`
- `issue_question`
- `thesis_hint`
- `novelty_score`
- `impact_score`
- `portfolio_relevance_score`
- `evidence_strength_score`
- `source_convergence_score`
- `delta_score`
- `redundancy_penalty`
- `total_score`
- `reason_codes_json`

#### `issue_candidate_events`

- `candidate_id`
- `event_id`
- `relation_kind`

#### `selection_contexts`

- `selection_context_id`
- `run_id`
- `consumer_kind`
- `consumer_id`
- `selection_policy_version`
- `selected_by`
- `created_at`

#### `issue_selections`

- `selection_context_id`
- `candidate_id`
- `selected_rank`
- `selected`
- `selection_reason_codes_json`

### Existing Tables To Keep In Phase 1

- `documents`
- `chunks`
- `citations`
- `evidence_packs`
- `issue_maps`
- `structured_claims`

### Compatibility Rules

Current compatibility constraints that stay intact in Phase 1:

- `apps/agent/storage/sqlite_runtime.py`
  - still persists `evidence_packs.query_text`
- `apps/agent/pipeline/types.py`
  - `DailyBriefSynthesisStageData` still carries `query_text`, `evidence_pack_items`, and `issue_evidence_scopes`
- `evals/run_eval_suite.py`
  - retrieval cases still run through `query_text`

Phase 1 rules:

- add new tables without deleting old ones
- keep `query_text` end to end for backward compatibility, even if it becomes derived or placeholder data on the daily-brief path
- keep `issue_maps` and `structured_claims` flowing so renderer and validator do not need a same-phase rewrite

### Dual-Written Artifacts

Phase 1 should dual-write:

- `event_clusters.json`
- `event_assessments.json`
- `market_snapshot.json`
- `issue_candidates.json`
- `selection_contexts.json`
- `issue_selections.json`

## Feature Flag

Phase 1 should be rollout-gated.

Recommended config shape:

- `ISSUE_DISCOVERY_MODE=baseline|shadow|primary`

Behavior:

- `baseline`
  - current `query_text` path remains authoritative
  - no selection effect from issue discovery v0
- `shadow`
  - issue discovery v0 runs and persists artifacts
  - current baseline still decides the brief
  - selector outputs are evaluated side by side
- `primary`
  - issue discovery v0 becomes authoritative for daily-brief issue selection
  - baseline artifacts may still be written for regression comparison during the rollout window

## Reuse Of Existing `issue_dedup`

Phase 1 should not delete `apps/agent/daily_brief/issue_dedup.py`.

Instead:

- keep its overlap logic
- keep its information-gain gate
- keep its issue-budget enforcement
- move or wrap that logic under `issue_discovery/selector.py`

In Phase 1, `issue_dedup` becomes the overlap and information-gain gate on top of scored candidates.

## Eval And Rollout

### Eval Strategy

Keep old retrieval evals as the baseline and add selector evals in parallel.

Phase 1 eval tracks:

- baseline `query_text` retrieval behavior
- issue-discovery shadow outputs
- overlap and information-gain behavior on candidate sets
- issue-selection outcomes for daily brief

### Shadow Rollout

Recommended rollout order:

1. land additive schema and artifact writing
2. run `shadow` mode on fixtures and eval suites
3. compare baseline issue outputs versus selector-driven outputs
4. switch `daily_brief` to `primary` only after thresholds are met

### Rollout Checks

Before promoting to `primary`, confirm:

- no regression in citation validation pass rate
- no regression in downstream renderer compatibility
- selected issues show lower duplicate or low-information-gain rates than baseline
- value-critic failures caused by weak issue choice trend down instead of up

## Success Metrics

Phase 1 succeeds when these outcomes hold for the daily-brief path:

- fewer selected issues are dropped for low information gain
- fewer selected issues are flagged as headline clusters without a thesis
- value-critic pass rate improves on selected issues
- citation validation does not regress
- duplicate-issue merges decrease because better candidates are produced upstream
- shadow mode shows selector outputs that are at least as evidence-grounded as the baseline path

## Explicit Non-Goals

Phase 1 is not:

- a rewrite of alerts
- a board/dashboard product design
- the final long-term schema
- permission to delete `query_text` compatibility immediately
- permission to delete existing daily-brief briefing and rendering contracts in the same change
