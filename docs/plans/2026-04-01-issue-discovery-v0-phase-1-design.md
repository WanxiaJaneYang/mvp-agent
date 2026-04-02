# Phase 1: Issue Discovery v0

Issue anchor: GitHub issue [#193](https://github.com/WanxiaJaneYang/mvp-agent/issues/193)

## Goal

Introduce a first additive `issue_discovery v0` path that improves daily-brief issue selection without forcing a same-phase rewrite of retrieval, rendering, runtime storage, or alert delivery.

Phase 1 should change what the system chooses to talk about, while keeping the existing downstream brief path as intact as possible.

## Scope

Phase 1 covers:

- core object contracts
- two-stage scoring
- additive schema
- feature flag and iteration budgets
- eval and rollout
- success metrics

Phase 1 does not cover:

- alert-policy redesign
- board/dashboard product design
- deletion of the old `query_text` path
- a same-phase rewrite of current briefing and rendering contracts

## Phase 1 Consumer

The first consumer for `issue_discovery v0` is `daily_brief`.

Alerts and board/dashboard consumers may later reuse shared event and scoring primitives, but they are not in Phase 1 rollout scope. This avoids forcing alert policy into a daily-brief selection model.

Implementation follow-on:

- `docs/plans/2026-04-02-issue-discovery-v0-implementation-spec.md`

## Target Flow

Phase 1 adopts a two-stage selector and a bounded review loop:

`market_stream -> candidate_builder -> cheap_scoring -> shortlist -> issue_enricher -> rerank/select -> briefing -> critic + hard_gate -> daily_brief`

### Stage A: Candidate Recall

Purpose:

- generate issue candidates from events
- score them cheaply
- keep only a top-K shortlist

Expected properties:

- mostly deterministic
- cheap enough to run across the whole daily event set
- no recursive full-corpus research

### Stage B: Candidate Enrich + Rerank

Purpose:

- spend extra retrieval and reasoning only on shortlisted issues
- answer open questions
- test hypotheses
- improve the evidence basis before final selection

Expected properties:

- bounded by explicit iteration budgets
- targeted rather than broad
- able to rerank or drop shortlisted issues after enrichment

### Stage C: Briefing Review Loop

Purpose:

- assemble issue-specific evidence
- compose claims
- review, route revisions, and gate the final artifact

Phase 1 downstream split:

- `evidence_assembler`
- `claim_composer`
- `integrity_critic`
- `value_gate`
- `revision_router`
- `hard_gate`

## Core Object Contracts

Each core object contract below defines:

- primary key
- upstream inputs
- downstream consumers
- scope

### `Event`

Primary key:
- `event_id`

Upstream inputs:
- canonicalized market/news items
- clustering metadata

Downstream consumers:
- `IssueCandidate`
- alert ranking
- board ranking

Scope:
- persistent
- canonical
- not product-scoped

Required fields:

- `event_id`
- `cluster_key`
- `entity_ids`
- `time_window`
- `source_ids`
- `headline_summary`
- `market_tags`
- `market_impact_hints`

Phase 1 note:
- this is the top-level event object
- cluster identity is document/news-item centric, not chunk centric
- representative chunk IDs may be attached for evidence pointers, but they do not define the event

### `IssueCandidate`

Primary key:
- `issue_id`

Upstream inputs:
- one or more `Event` records
- optional market-state context
- prior-brief delta anchors

Downstream consumers:
- `issue_enricher`
- `rerank/select`
- `briefing`

Scope:
- run-scoped
- persistent
- not product-scoped

Required fields:

- `issue_id`
- `event_ids`
- `title`
- `why_now`
- `angle`
- `candidate_type`
- `pre_enrich_score`
- `status`

Allowed `status` values:

- `observed`
- `shortlisted`
- `enriched`
- `selected`
- `dropped`
- `held`

Phase 1 note:
- an issue candidate may combine multiple related events
- `pre_enrich_score` is the output of Stage A, not the final product policy decision
- multi-event membership should be materialized through `issue_candidate_events` with an explicit `relation_kind`

### `IssueEnrichment`

Primary key:
- `enrichment_id`

Upstream inputs:
- shortlisted `IssueCandidate`
- planner output
- targeted retrieval output

Downstream consumers:
- `rerank/select`
- `briefing`
- `revision_router`

Scope:
- run-scoped
- persistent
- not product-scoped

Required fields:

- `enrichment_id`
- `issue_id`
- `open_questions`
- `hypotheses`
- `evidence_requirements`
- `follow_up_queries`
- `evidence_ids`
- `post_enrich_score`
- `coverage_gaps`

Phase 1 note:
- this object is the place where research-like capability is contained
- enrichment is only allowed for shortlisted issues

### `ReviewIssue`

Primary key:
- `review_issue_id`

Upstream inputs:
- `integrity_critic`
- `value_gate`
- `hard_gate`

Downstream consumers:
- `revision_router`
- final publish decision

Scope:
- run-scoped
- persistent
- artifact-scoped

Required fields:

- `review_issue_id`
- `issue_type`
- `severity`
- `description`
- `requires_new_search`
- `suggested_query`
- `blocks_publish`

Phase 1 note:
- this object makes review findings routable instead of burying them in free-form critic text

## Issue Enricher Contract

Phase 1 should add a small enrichment orchestrator under `issue_discovery`, not a repo-wide agent framework.

Recommended flow:

`IssueCandidate -> planner -> targeted retrieval -> evidence extraction -> follow-up search -> enrichment summary -> post_enrich_score`

The planner output should stay narrow. It should only answer:

- what evidence types are needed
- what open questions remain
- what hypotheses are testable
- what follow-up queries are worth running

Research remains an enrichment step attached to shortlisted issues. It is not promoted into the system's top-level architecture.

## Two-Stage Scoring

Scoring should be split into three layers rather than one mixed total.

### A. `discovery_score`

Purpose:
- shared, cheap, upstream shortlist score

Used for:
- `candidate_builder -> cheap_scoring -> shortlist`

Primitives:

- `novelty`
- `breadth_of_coverage`
- `market_linkage`
- `persistence`
- `source_diversity`
- `entity_relevance`

Phase 1 initial formula:

`discovery_score = 0.22*novelty + 0.18*breadth_of_coverage + 0.20*market_linkage + 0.12*persistence + 0.14*source_diversity + 0.14*entity_relevance`

Range:
- `0.0` to `1.0`

Output field:
- `IssueCandidate.pre_enrich_score`

### B. `enrichment_score`

Purpose:
- shared, more expensive, downstream rerank score

Used for:
- post-shortlist reranking after targeted research

Primitives:

- `evidence_strength`
- `freshness`
- `source_quality`
- `explanatory_yield`
- `counter_view_coverage`
- `claimability`

Phase 1 initial formula:

`enrichment_score = 0.24*evidence_strength + 0.14*freshness + 0.16*source_quality + 0.18*explanatory_yield + 0.14*counter_view_coverage + 0.14*claimability`

Range:
- `0.0` to `1.0`

Output field:
- `IssueEnrichment.post_enrich_score`

### C. `product_policy_score`

Purpose:
- product-specific final ranking score

Phase 1 consumer:
- `daily_brief`

Daily-brief policy primitives:

- `value_density`
- `coverage_balance`
- `non_redundancy`
- `brief_fit`

Phase 1 initial daily-brief formula:

`product_policy_score = 0.32*value_density + 0.23*coverage_balance + 0.25*non_redundancy + 0.20*brief_fit`

Range:
- `0.0` to `1.0`

Phase 1 note:
- alerts keep their own trigger policy and do not consume this formula
- board/dashboard ranking can later define its own product policy score

### Score Persistence

Every persisted score in Phase 1 should carry:

- numeric value
- scoring version
- reason codes

Phase 1 clarification:

- `confidence_score` is not a selector input in V0
- if a later implementation persists `confidence_score`, it is for operator inspection only
- `redundancy_penalty`, if used as an internal helper for `non_redundancy`, must be in `[0,1]`
- `redundancy_penalty=0` means no redundancy
- `redundancy_penalty=1` means high redundancy
- the helper penalty is applied only once

### Selection Sequence

Phase 1 selection should follow this order:

1. compute `discovery_score` for all candidates
2. keep only top-K shortlist
3. enrich shortlisted candidates
4. compute `enrichment_score`
5. drop candidates below enrichment floors
6. compute `product_policy_score` for the daily brief consumer
7. select final daily-brief issues

This is intentionally not a one-shot universal total score.

## Additive Schema

### New Tables

#### `events`

- `event_id`
- `cluster_key`
- `entity_ids_json`
- `time_window_start`
- `time_window_end`
- `source_ids_json`
- `headline_summary`
- `market_tags_json`
- `market_impact_hints_json`
- `cluster_version`

#### `event_items`

- `event_id`
- `news_item_id`
- `doc_id`
- `representative_chunk_id`
- `role_hint`
- `similarity_score`

#### `issue_candidates`

- `issue_id`
- `discovery_run_id`
- `policy_version`
- `event_ids_json`
- `title`
- `why_now`
- `angle`
- `candidate_type`
- `pre_enrich_score`
- `status`
- `reason_codes_json`

#### `issue_candidate_events`

- `issue_id`
- `event_id`
- `relation_kind`

#### `issue_enrichments`

- `enrichment_id`
- `issue_id`
- `enrichment_round`
- `open_questions_json`
- `hypotheses_json`
- `evidence_requirements_json`
- `follow_up_queries_json`
- `evidence_ids_json`
- `post_enrich_score`
- `coverage_gaps_json`
- `reason_codes_json`

#### `review_issues`

- `review_issue_id`
- `run_id`
- `artifact_id`
- `issue_id`
- `issue_type`
- `severity`
- `description`
- `requires_new_search`
- `suggested_query`
- `blocks_publish`
- `route_target`

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
- `issue_id`
- `product_policy_score`
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

- `events.json`
- `issue_candidates.json`
- `issue_enrichments.json`
- `review_issues.json`
- `selection_contexts.json`
- `issue_selections.json`

## Feature Flag And Iteration Budgets

### Mode Flag

Recommended config:

- `ISSUE_DISCOVERY_MODE=baseline|shadow|primary`

Behavior:

- `baseline`
  - current `query_text` path remains authoritative
- `shadow`
  - issue discovery v0 runs and persists artifacts
  - baseline still decides the brief
- `primary`
  - issue discovery v0 becomes authoritative for daily-brief issue selection

### Iteration Budgets

Only shortlisted issues may enter iterative enrichment or revision.

Recommended controls:

- `MAX_SHORTLIST_SIZE`
- `MAX_FOLLOWUP_QUERIES_PER_ISSUE`
- `MAX_ENRICHMENT_ROUNDS`
- `MAX_REVISION_ROUNDS`

This makes the framework shallow for alerts later, medium-depth for daily brief, and still bounded for other products.

## Reuse Of Existing `issue_dedup`

Phase 1 should not delete `apps/agent/daily_brief/issue_dedup.py`.

Instead:

- keep its overlap logic
- keep its information-gain gate
- keep its issue-budget enforcement
- move or wrap that logic under `issue_discovery/selector.py`

In Phase 1, `issue_dedup` becomes the overlap and information-gain gate applied after cheap scoring and again after enrichment rerank where needed.

## Briefing Review And Routing

### Split Critics

Phase 1 should treat these as distinct concepts:

- `integrity_critic`
  - unsupported claim
  - stale source
  - weak evidence
  - numeric mismatch
  - one-sided framing
- `value_gate`
  - whether the issue deserves brief space
  - whether it adds new explainability
  - whether it duplicates another issue
  - whether it meets the product value threshold

### Fixed Revision Routing

Routing should be rule-driven:

- missing source, stale source, weak evidence, numeric mismatch
  - route back to `issue_enricher`
- evidence adequate but expression or structure poor
  - route back to `claim_composer`
- low value or high duplication
  - drop
- passes all gates
  - render

This should not be left to unconstrained LLM judgment.

## Hard Gates

Phase 1 should add these hard gates:

### `claim_evidence_gate`

- every key claim must bind to explicit `evidence_id`

### `numeric_claim_gate`

- numeric, time, price-move, valuation, and guidance claims must have a checkable source

### `freshness_gate`

- claim types may have different freshness policies

### `source_floor_gate`

- some issue types require Tier 1 or Tier 2 source coverage

### `final_artifact_gate`

- the final rendered brief artifact is gated, not just intermediate sections

### Prohibited Behaviors

Phase 1 should explicitly forbid:

- filling an issue section with generic global facts when no issue-specific evidence exists
- letting the writer generate citations without deterministic validation

## Eval And Rollout

### Shadow Eval

Phase 1 should run against the current daily-brief selector in parallel.

Comparison set:

- current selector
- issue discovery v0 in `shadow`

### Eval Metrics

Track at least:

- `precision@N` for selected issues
- duplicate rate
- unsupported-claim rate
- analyst preference
- cost
- latency

### Rollout Order

1. land object contracts and additive schema
2. land two-stage scoring and shortlist flow
3. add the small enrichment orchestrator
4. split briefing review into integrity, value, routing, and hard gates
5. run shadow eval against the current selector
6. promote to `primary` only after thresholds are met

## Success Metrics

Phase 1 succeeds for the daily-brief path when:

- selected issues are less repetitive than the current selector output
- unsupported-claim rate declines
- analyst preference improves against the current selector baseline
- cost and latency stay within accepted rollout budgets
- citation validation does not regress
- value-gate pass rate improves because issue choice improved upstream

## Explicit Non-Goals

Phase 1 is not:

- a rewrite of alerts
- a board/dashboard product design
- the final long-term schema
- permission to delete `query_text` compatibility immediately
- permission to delete existing daily-brief briefing and rendering contracts in the same change
