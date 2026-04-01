# Market Intelligence Pipeline + Brief Products Redesign

## Goal

Reframe the repository from a `daily_brief` generation pipeline into a reusable market-intelligence pipeline that discovers market events and issues first, then powers brief products on top of that intelligence layer.

This redesign should make the repo behave like:

`ingest -> canonicalize -> cluster events -> score issues -> select issues -> assemble issue evidence -> compose claims -> gate on integrity and value -> deliver products`

not like:

`collect documents -> form one corpus query -> grow a brief from the query`

## Status And Scope

- redesign only; no runtime changes are part of this document
- extends existing issue-centered daily-brief work instead of replacing it
- changes repo architecture, ownership boundaries, and staged rollout order
- after this redesign lands, the repo should follow the required next step:
  - planning issue/PR
  - child issues if the plan splits into multiple streams
  - implementation PRs

## Why A Repo-Level Redesign Is Needed

The current repo has already improved the downstream shape of the daily brief:

- issue-centered synthesis
- structured claims
- critic and publish-decision plumbing

That work improved the output contract, but it did not change the upstream discovery model enough. The current runtime still treats the daily brief as the place where market discovery, issue selection, evidence assembly, and delivery all happen together.

Verified current pressure points:

- `apps/agent/daily_brief/runner.py`
  - `build_daily_brief_query()` still compresses the day into a high-frequency token query
  - the main runner still builds one broad evidence pack before issue selection is truly settled
- `apps/agent/daily_brief/editorial_planner.py`
  - `plan_brief_locally()` still depends on `_candidate_issue_seeds()`
  - `_candidate_issue_seeds()` is still a token-frequency seed generator
- `apps/agent/daily_brief/issue_retrieval.py`
  - `counter`, `minority`, and `watch` still depend on lexical buckets such as `OPPOSING_TERMS`, `MINORITY_TERMS`, and `WATCH_TERMS`
- `apps/agent/daily_brief/critic.py`
  - the critic blocks obvious analytical shallowness, but it still does not decide whether a selected issue is worth publishing
- `apps/agent/daily_brief/runner.py`
  - `_publish_summary()` still resolves publication from citation/integrity status, not from a first-class value gate

The result is a structural mismatch:

- the repo can now render issue-shaped briefs
- but it still discovers those issues from corpus-frequency and section-bucket logic

In practice, the system still grows a brief from a pile of documents instead of growing selected issues from a market-state view.

## Design Principles

1. Event-centric before issue-centric.
2. Issue discovery before issue enrichment.
3. Score before summarize.
4. Separate intelligence infrastructure from products.
5. Keep lower layers deterministic, local-first, and citation-grounded.
6. Make value gating explicit rather than implicit.
7. Reuse shared event models and score primitives across products, while allowing product-specific selection policies.

## Existing Design Work To Preserve

This redesign keeps the useful parts of recent daily-brief work:

- `docs/plans/2026-03-11-daily-brief-issue-centric-design.md`
  - keep issue-centered output as the downstream brief contract
- `docs/plans/2026-03-12-daily-brief-model-layer-redesign-design.md`
  - keep structured issue-planner and claim-composer layers
- `docs/plans/2026-03-12-brief-editorial-planner-design.md`
  - keep editorial planning, but demote it to a downstream product-shaping concern
- `docs/plans/2026-03-12-claim-delta-and-publish-gate-design.md`
  - keep claim delta and publish-decision contracts, but add a value gate upstream of publication

The core change in this redesign is not "replace issue-centered briefing." It is "stop treating issue-centered briefing as the whole architecture."

## Approaches Considered

### Option A: Keep `apps/agent/daily_brief/` as the main architecture and tune prompts/heuristics

This would keep the repo mostly intact and try to improve:

- issue seeds
- evidence bucketing
- critic prompts

Why it is not preferred:

- it leaves discovery logic embedded inside a product package
- it keeps corpus-first issue formation as the default mental model
- it makes future products depend on daily-brief internals

### Option B: Add a stronger issue-discovery layer, but keep it inside `apps/agent/daily_brief/`

This would add event clustering and issue scoring, but still treat `daily_brief` as the top-level owner.

Why it is better than Option A:

- improves selection quality
- reduces direct dependence on corpus token frequency

Why it is still not preferred:

- discovery would remain product-owned instead of platform-owned
- alerts and future dashboard/board outputs would still duplicate or bypass the same logic
- the repo boundary between infrastructure and products would stay unclear

### Option C: Reframe the repo around market intelligence, with brief products on top

This redesign introduces a layered architecture:

- `market_stream`
- `issue_discovery`
- `briefing`
- `products`

Why this is preferred:

- aligns architecture with the real bottleneck: issue discovery and selection
- lets daily brief become one consumer instead of the orchestrator of everything
- gives alerts and board-style outputs the same upstream event and issue model
- preserves existing briefing work while putting it in the right layer

## Selected Architecture

### Top-Level Repo Shape

```text
apps/agent/
  market_stream/
    canonicalize.py
    event_cluster.py
    event_features.py
    event_store.py
    event_snapshot.py

  issue_discovery/
    candidate_builder.py
    scoring.py
    selector.py
    framing.py

  briefing/
    evidence_query.py
    evidence_rerank.py
    argument_map.py
    claim_composer.py
    value_critic.py
    render_contract.py

  products/
    daily_brief/
      runner.py
    alerts/
      runner.py
    board/
      runner.py
```

Shared lower-level packages such as `ingest`, `retrieval`, `storage`, and `runtime` remain infrastructure and should not become product-specific.

### Core Object Contracts

#### `canonical_news_item`

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

Notes:
- In Phase 1 this can stay as a lightweight projection over `documents`, with `news_item_id` initially aliasing `doc_id` if that avoids unnecessary table churn.

#### `event_cluster`

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

Notes:
- Clustering is news-item or document centric, not arbitrary chunk centric.
- `chunk_id` links may be stored as representative evidence pointers, but they do not define cluster identity.

#### `daily_market_snapshot`

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

Notes:
- This is not a canonical cross-run market object. It is a derived, reproducible run artifact that records how the system saw the day.

#### `issue_candidate`

Primary key:
- `candidate_id`

Upstream inputs:
- one or more `event_cluster` records
- optional `daily_market_snapshot`
- prior-brief or prior-run delta anchors

Downstream consumers:
- `selector`
- `briefing`
- product-specific selection contexts

Scope:
- run-scoped
- persistent
- not product-scoped

Notes:
- An issue candidate may map to one event or multiple related events. It should not be constrained to exactly one event cluster.

#### `issue_selection`

Primary key:
- `(selection_context_id, candidate_id)`

Upstream inputs:
- `issue_candidate[]`
- selection policy and consumer context

Downstream consumers:
- `products/daily_brief`
- `products/alerts`
- `products/board`

Scope:
- run-scoped
- persistent
- consumer-scoped

Notes:
- Selection is not daily-brief-only. The parent `selection_context_id` carries `consumer_kind`, `consumer_id`, `selection_policy_version`, and `selected_by`.

### Layer 1: `market_stream`

Purpose:

- turn raw daily documents into canonical news items
- deduplicate repeated coverage into event clusters
- derive a daily internal market snapshot

This layer sits after existing fetch/extract/normalize/dedup/chunk work.

Outputs:

- canonical news item records
- event clusters
- daily market snapshot artifacts

This is the layer that solves the current "same event told by many articles" problem before issue generation starts.

### Layer 2: `issue_discovery`

Purpose:

- grow issue candidates from event clusters, not from corpus token frequency
- allow one issue candidate to combine multiple related event clusters when the market question spans more than one event
- score and rank issue candidates
- keep only the few issues worth downstream enrichment

Selection should persist explicit reason codes such as:

- `high_novelty`
- `broad_market_transmission`
- `supported_by_official_and_market_media`
- `high_portfolio_relevance`

The first implementation does not need an LLM-heavy selector. Rules-first scoring is acceptable, with optional model reranking only for close decisions or issue phrasing.

### Layer 3: `briefing`

Purpose:

- work only on already selected issues
- retrieve, rerank, and prune evidence per issue
- compose issue-anchored claims
- gate on analytical value as well as integrity

This layer keeps the useful issue-centered synthesis and claim-composition work already present in the repo, but changes the upstream contract:

- input is no longer "one global corpus query"
- input becomes "selected issue + event context + prior brief delta anchor"

Evidence roles should be determined by relation to the selected issue, not by lexical trigger words. The key dimensions are:

- event role
- evidence stance
- time horizon
- falsification signal

### Layer 4: `products`

Purpose:

- turn the same intelligence layer into user-facing outputs

Products should include:

- daily brief
- alerts
- board/dashboard feeds

The product layer should not be responsible for first discovering what matters. It should only decide how selected issues are rendered, bundled, and delivered.

### Product Policy Boundaries

The redesign should not be interpreted as "one literal selector shared unchanged across every product."

What should be shared:

- event clusters
- assessment primitives
- issue candidates
- score inputs and reason-code vocabulary where the semantics are actually shared

What can stay product-specific:

- daily brief
  - issue selection
  - issue enrichment
  - value-gated publication
- alerts
  - event trigger logic
  - category floors
  - cooldown and daily caps
  - evidence quality gate
- board/dashboard
  - event ranking
  - operator visibility
  - dropped-vs-selected explainability

The correct architectural claim is:

- share the event model and score primitives
- do not force a single identical selection policy onto daily brief, alerts, and board consumers

This should align with the current alert path in `apps/agent/alerts/scoring.py` and `artifacts/modelling/alert_scoring.md`, not replace those policy gates with a daily-brief-style issue selector.

### Score Primitive Contract

All first-pass scoring primitives should use a `0.0` to `1.0` range and persist both the numeric score and the reason codes that produced it.

#### `novelty_score`

- level: event assessment and issue candidate
- meaning: how different the event or issue is relative to prior brief or prior run context
- note: this is contextual and must never live only on the canonical event record

#### `impact_score`

- level: event assessment and issue candidate
- meaning: expected market transmission breadth and materiality
- note: alerts may reuse this primitive, but still apply separate category-specific floors

#### `portfolio_relevance_score`

- level: issue candidate
- meaning: relevance to the repo's target retail ETF-holder audience
- note: this is not a canonical event property

#### `evidence_strength_score`

- level: issue candidate
- meaning: adequacy of direct evidence after source-quality, recency, and citation coverage checks
- note: this is about whether the candidate can support a credible issue write-up

#### `source_convergence_score`

- level: event assessment and issue candidate
- meaning: whether distinct publishers and source roles converge on the same underlying development
- note: this is intentionally different from `evidence_strength_score`; convergence measures agreement across independent source paths, not total evidence adequacy

#### `redundancy_penalty`

- level: issue candidate
- meaning: overlap with already-kept issues or with low-information-gain restatements
- note: this should align with the current overlap and information-gain gates

#### Initial Total Score Formula

For Phase 1, the issue candidate total score should be explicit and simple:

`total_score = 0.25*novelty + 0.25*impact + 0.20*portfolio_relevance + 0.15*evidence_strength + 0.15*source_convergence - 0.20*redundancy_penalty`

This formula is a starting policy, not a permanent truth. It should be versioned.

#### Tie-Break Rules

If total score ties within the configured tolerance:

1. prefer higher `novelty_score`
2. then higher `impact_score`
3. then broader official plus market-media source-role coverage
4. then stronger delta versus prior brief

#### Selection Veto Conditions

An issue candidate should still be dropped even with a high total score when any of these hold:

- `evidence_strength_score` is below the minimum evidence floor
- the candidate collapses into an already-kept issue under overlap or information-gain gating
- the candidate has no distinct thesis beyond a repeated headline cluster
- the candidate cannot produce a substantive counter or watch path

### Market Snapshot Contract

The market snapshot should be treated as a versioned run artifact, not a loose concept.

Phase 1 contract:

- taxonomy is fixed but versioned
- an event may map to multiple lenses
- if no configured lens matches, the event falls into `other`
- snapshot rows may feed scoring, explainability, and issue framing, but those consumers should read different fields for different purposes

Minimum fields:

- `snapshot_id`
- `run_id`
- `taxonomy_version`
- `lens`
- `event_ids_json`
- `lens_summary_json`
- `score_inputs_json`
- `operator_notes_json`

This keeps the snapshot useful for operators without turning it into the canonical source of issue identity.

## Target Pipeline

### Stages 1-5: Keep The Existing Intake Backbone

These stages remain structurally correct and should stay reusable:

1. fetch
2. extract
3. normalize
4. dedup
5. chunk/index

### Stage 6: `market_stream`

Input:

- newly ingested and indexed documents for the run

Output:

- canonical news items
- event clusters
- daily market snapshot

The daily market snapshot is an internal state board, not the end-user brief. It should capture the day across a few market lenses such as rates, inflation, labor, growth, oil, USD, megacap, and geopolitics.

### Stage 7: `issue_discovery`

Input:

- event clusters
- daily market snapshot
- optional prior-brief delta context

Output:

- issue candidates with score breakdowns
- selected issues with explicit selection reasons

Only the top one or two issues should normally proceed to daily-brief briefing, but other consumers may apply different downstream thresholds through their own selection contexts.

### Stage 8: Issue-Anchored Evidence Assembly

Input:

- selected issue
- seed evidence from the related event cluster
- prior brief delta anchor

Actions:

- hybrid search
- reranking
- source filtering
- evidence pruning

This stage should reuse existing retrieval infrastructure, but the retrieval frame must become issue-scoped instead of corpus-scoped.

### Stage 9: Claim Composition + Integrity Gate + Value Gate

Output should remain structured and inspectable:

- issue maps
- claim objects
- validator report
- critic report
- publish decision

Publication should require all of:

- citation status is acceptable
- integrity checks pass
- value critic passes

### Stage 10: Product Delivery

Products consume the same selected-issue layer:

- daily brief renders the strongest issues for the day
- alerts reuse shared event and score primitives, but keep their own trigger and policy gate
- board/dashboard views expose live event and issue state for operator inspection

## Current-To-Target File Mapping

### `apps/agent/daily_brief/runner.py`

Current role:

- orchestration
- corpus query building
- evidence-pack assembly
- planner setup
- publication decision

Target role split:

- `apps/agent/products/daily_brief/runner.py`
  - product orchestration only
- `apps/agent/market_stream/*`
  - event-layer generation
- `apps/agent/issue_discovery/*`
  - candidate generation, scoring, selection
- `apps/agent/briefing/*`
  - issue evidence assembly, claims, value gating

### `apps/agent/daily_brief/editorial_planner.py`

Keep the editorial-planning idea, but narrow it to:

- issue budget
- render mode
- brief thesis
- key takeaways
- watchlist layout

It should no longer own candidate issue generation.

### `apps/agent/daily_brief/issue_retrieval.py`

Rename and redesign this module into issue-scoped evidence assembly, for example:

- `apps/agent/briefing/issue_evidence_assembly.py`
- or `apps/agent/briefing/argument_evidence.py`

It should stop deriving `counter`, `minority`, and `watch` from lexical term buckets.

### `apps/agent/daily_brief/critic.py`

Keep the integrity critic, but add a new value critic.

Minimum value-critic reason codes:

- `issue_not_material`
- `headline_cluster_without_thesis`
- `no_meaningful_delta_vs_prior`
- `counter_not_substantive`
- `generic_why_it_matters`
- `weak_watch_signal`
- `selected_issue_below_threshold`

### `apps/agent/retrieval/evidence_pack.py`

Keep this as reusable retrieval infrastructure, but do not let a single corpus-level `query_text` remain the primary selector for the daily brief path.

## Data Model Redesign

The current data model centers evidence packs around `query_text`. The redesigned model should center the repo on `event` and `issue`.

### New Tables

#### `event_clusters`

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

### Existing Tables To Preserve

- `documents`
- `chunks`
- `citations`

### Existing Tables To Reframe

- `evidence_packs`
  - keep, but move from corpus-scoped packs toward issue-scoped packs
  - `query_text` should become optional or secondary metadata, not the architectural center
- `issue_maps`
- `structured_claims`
  - keep, but source them from `issue_candidates -> issue_selections`

### Canonical Versus Contextual Persistence Rule

Canonical tables should only store identity and stable structural fields.

Do not store run-relative assessments such as:

- novelty versus prior brief
- impact under a particular consumer profile
- confidence tied to one clustering or scoring run

Those belong in run-scoped assessment tables keyed by at least:

- `run_id`
- `profile_id`
- `scoring_version`

## Value Gate Contract

The current publish contract separates citation status and analytical status. The redesigned contract should preserve that split and add explicit issue value as a first-class publish condition.

Expected decision fields:

- `citation_status`
- `analytical_status`
- `value_status`
- `publish_decision`
- `reason_codes`
- `delivery_mode`

`publish_decision=publish` should require passing value checks, not just the absence of hard integrity failure.

## Phase 1 Additive Migration Contract

This redesign must migrate additively first.

Current compatibility constraints that should remain intact in Phase 1:

- `apps/agent/storage/sqlite_runtime.py`
  - still persists `evidence_packs.query_text`
- `apps/agent/pipeline/types.py`
  - `DailyBriefSynthesisStageData` still carries `query_text`, `evidence_pack_items`, and `issue_evidence_scopes`
- `evals/run_eval_suite.py`
  - retrieval cases still run through `query_text`

Phase 1 migration rules:

- add new event, assessment, snapshot, candidate, and selection tables without deleting old tables
- keep `query_text` end to end for backward compatibility, even if it becomes a derived or placeholder field on the daily-brief path
- dual-write new selector artifacts beside existing brief artifacts
- keep old retrieval evals as the baseline and add selector evals in parallel
- compare baseline `query_text` retrieval against selector-driven issue selection before deleting any old path
- keep `issue_maps` and `structured_claims` flowing so the renderer and validator do not need a same-phase rewrite

Recommended dual-written artifacts in Phase 1:

- `event_clusters.json`
- `event_assessments.json`
- `market_snapshot.json`
- `issue_candidates.json`
- `selection_contexts.json`
- `issue_selections.json`

## Minimal Refactor Path

This redesign should not be implemented as a big-bang rewrite.

### Phase 1: Add Event Clusters And Issue Scoring

Replace the current corpus-first issue-seed logic in:

- `build_daily_brief_query()`
- `_candidate_issue_seeds()`

with:

- event clusters
- issue candidates
- score + selection

Keep current claim composition and rendering as intact as possible in this phase.

Phase 1 should also explicitly reuse the current `apps/agent/daily_brief/issue_dedup.py` logic instead of deleting it.

Recommended handling:

- keep `issue_dedup` behavior
- move or wrap it under `issue_discovery/selector.py`
- treat it as the overlap and information-gain gate on top of scored candidates

That preserves the existing overlap, information-gain, and issue-budget logic while the new candidate builder is still stabilizing.

This is the highest-leverage first cut because it changes what the system chooses to talk about.

### Phase 2: Replace Lexical Evidence Bucketing With Issue-Anchored Assembly

After issue selection improves, refactor evidence assembly so the repo stops using lexical section buckets for `counter`, `minority`, and `watch`.

This phase tightens evidence scope around selected issues instead of trying to "improve prompts" on weak issues.

### Phase 3: Add Value Critic And Operator Visibility

Add operator-facing artifacts or dashboard views for:

- today's event clusters
- issue candidates with score breakdown
- selected issues and why they were selected
- dropped issues and why they were dropped

This becomes the main control panel for explaining why a generated brief is or is not worth shipping.

## Non-Goals

- do not optimize for multi-agent orchestration as the core architecture
- do not turn the repo into a long-form research-report generator first
- do not force the first issue-discovery implementation to depend on an LLM
- do not replace the deterministic ingestion and citation backbone
- do not let alerts become a separate second discovery system

## Acceptance Checks For This Redesign

- the repo architecture is described in terms of `market_stream -> issue_discovery -> briefing -> products`
- selected issues no longer originate from corpus token frequency
- issue-scoped retrieval happens after issue selection, not before
- publication requires value gating in addition to citation and integrity checks
- daily brief, alerts, and board/dashboard outputs can all consume the same upstream intelligence layer
- existing issue-centered brief contracts remain usable as downstream consumers rather than top-level architecture

## Follow-On Planning Required After This Redesign

After this redesign is accepted, the next planning work should update:

- `artifacts/modelling/pipeline.md`
- `artifacts/modelling/data_model.md`
- `apps/agent/pipeline/types.py`
- runtime package ownership under `apps/agent/`
- the implementation roadmap and child issues for each major stream

That follow-on planning should land before implementation begins.
