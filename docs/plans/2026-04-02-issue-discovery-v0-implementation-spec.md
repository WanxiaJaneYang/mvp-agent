# Issue Discovery V0 Implementation Spec

Issue anchor: GitHub issue [#193](https://github.com/WanxiaJaneYang/mvp-agent/issues/193)

## Purpose

Turn the current `Phase 1: Issue Discovery v0` design into an implementation-ready spec for the first PR sequence.

This document is intentionally narrower and harder than the design doc. It defines the minimum V0 behavior needed to start implementation without reopening core contracts in every PR.

## Implementation Clarifications

### `confidence_score`

V0 does not use `confidence_score` in any selection total.

If `confidence_score` is persisted later, it is operator-inspection only and must not act as a hidden bonus term for:

- `discovery_score`
- `enrichment_score`
- `product_policy_score`

### `relation_kind`

V0 uses this minimal enum for `issue_candidate_events.relation_kind`:

- `primary_driver`
- `supporting_context`
- `cross_signal`
- `falsification_context`

Definitions:

- `primary_driver`
  - the event that defines the candidate title and `why_now`
- `supporting_context`
  - background or confirming context that strengthens the thesis
- `cross_signal`
  - a separate but relevant market signal that increases explanatory value
- `falsification_context`
  - a signal that could weaken, invalidate, or bound the candidate thesis

### `redundancy_penalty`

If used as an internal helper:

- `redundancy_penalty in [0,1]`
- `0` means no redundancy penalty
- `1` means high redundancy penalty
- it is applied only once
- if `product_policy_score` uses `non_redundancy`, then `non_redundancy = 1 - redundancy_penalty`

## 1. Event Clustering V0

### Input Unit

The clustering input unit is `canonical_news_item`.

V0 does not cluster raw chunks directly.

Representative chunks may be attached later for evidence pointers, but cluster identity is defined at the canonical-news-item level.

### Run Strategy

V0 clustering is a per-run rebuild over the current run's eligible `canonical_news_item` set.

This is the simplest implementation that supports:

- shadow evaluation
- deterministic reruns
- additive rollout without cross-run merge complexity

Cross-run continuity should rely on `cluster_key` comparisons, not on assuming `event_id` stability across runs in V0.

### Similarity Features

V0 pairwise similarity should consider only a small set of deterministic features:

- normalized headline token overlap
- entity overlap
- market-tag overlap
- time-window proximity
- canonical URL or duplicate-source suppression

Recommended weighted similarity:

- `0.40 * headline_overlap`
- `0.25 * entity_overlap`
- `0.20 * market_tag_overlap`
- `0.15 * time_proximity`

V0 should not use an unconstrained semantic model here.

### Clustering Strategy

V0 strategy:

1. generate candidate pairs only within the same run
2. drop pairs that are too far apart in time
3. score remaining pairs with the deterministic similarity function
4. connect pairs above threshold
5. materialize clusters as connected components or greedy merged sets

Recommended initial merge threshold:

- `similarity_score >= 0.65`

### `canonical_title`

Choose `canonical_title` from the cluster item with the strongest priority:

1. higher source tier
2. cleaner or more specific headline
3. earlier publication time when ties remain

This should be deterministic.

### `cluster_version`

`cluster_version` means clustering algorithm version, not output instance version.

### V0 Outputs

Artifacts:

- `events.json`
- `event_items.json`
- `clustering_report.json`

Minimum report fields:

- run ID
- input item count
- cluster count
- singleton count
- average cluster size
- clustering version

## 2. Candidate Builder V0

### Single-Event Candidate Rule

V0 base rule:

- create at most one base candidate per eligible event
- the base candidate takes that event as `primary_driver`

An event is eligible for a base candidate when it clears minimum discovery floors for:

- market linkage
- source diversity
- entity relevance

### Multi-Event Combination Rule

V0 multi-event combination is deliberately narrow.

A multi-event candidate may be formed only when:

- there is one clear `primary_driver`
- additional events share either:
  - a market lens
  - a tracked entity or entity family
  - a clear causal or falsification relationship

V0 does not allow arbitrary many-to-many event bundles.

Recommended limit:

- one `primary_driver`
- up to two auxiliary events

### `relation_kind` Assignment

Assignment rules:

- `primary_driver`
  - exactly one per candidate
- `supporting_context`
  - same market question, mainly confirming or contextual
- `cross_signal`
  - a different domain signal that strengthens market relevance
- `falsification_context`
  - evidence that could cap, weaken, or disprove the issue thesis

### Candidate Budget

Recommended V0 budgets:

- `MAX_CANDIDATES_PER_EVENT = 1`
- `MAX_MULTI_EVENT_CANDIDATES_PER_RUN = 5`
- `MAX_TOTAL_CANDIDATES_PER_RUN = 20`
- `MAX_SHORTLIST_SIZE = 8`

These are rollout defaults, not permanent values.

### Candidate Builder Outputs

Artifacts:

- `issue_candidates.json`
- `issue_candidate_events.json`
- `candidate_builder_report.json`

Minimum report fields:

- input event count
- candidate count
- single-event candidate count
- multi-event candidate count
- dropped-by-budget count

## 3. Score Features V0

This section defines feature-level inputs for every V0 primitive that participates in selection.

### A. Discovery Score Features

#### `novelty`

Inputs:

- prior brief issue titles
- prior run cluster keys
- first-seen timestamp
- new entity or new entity-pair signals

Base rule:

- score higher when the event or candidate introduces a new cluster key or new entity combination relative to recent runs

Reason codes:

- `new_cluster_key`
- `new_entity_pair`
- `recently_seen`

#### `breadth_of_coverage`

Inputs:

- source count
- publisher count
- source-role count

Base rule:

- score higher when the issue appears across multiple distinct publishers and source roles, capped to avoid runaway rewards for volume alone

Reason codes:

- `broad_coverage`
- `limited_coverage`

#### `market_linkage`

Inputs:

- market tags
- market impact hints
- affected asset or macro lenses

Base rule:

- score higher when the event clearly links to market-relevant transmission paths rather than being a generic headline

Reason codes:

- `direct_market_link`
- `indirect_market_link`
- `weak_market_link`

#### `persistence`

Inputs:

- first seen time
- last seen time
- within-run recurrence

Base rule:

- score higher when the signal persists beyond one isolated mention, while still allowing genuinely new events to win on novelty

Reason codes:

- `persistent_signal`
- `one_off_signal`

#### `source_diversity`

Inputs:

- unique publishers
- tier mix
- official plus market-media presence

Base rule:

- score higher when the issue is supported by diverse publishers and not dominated by one weak path

Reason codes:

- `diverse_sources`
- `single_publisher_dominance`
- `official_and_media_present`

#### `entity_relevance`

Inputs:

- entity IDs
- market tags
- ETF-holder relevance heuristics

Base rule:

- score higher when the issue touches macro, index, sector, rate, FX, commodity, or megacap exposures that matter to the repo's target user

Reason codes:

- `high_etf_holder_relevance`
- `moderate_etf_holder_relevance`
- `low_etf_holder_relevance`

### B. Enrichment Score Features

#### `evidence_strength`

Inputs:

- evidence count
- citation coverage
- directness of evidence to the issue thesis

Base rule:

- score higher when the candidate has multiple issue-specific evidence items that directly support the thesis and its challenge paths

Reason codes:

- `strong_issue_specific_evidence`
- `thin_evidence`
- `missing_counter_evidence`

#### `freshness`

Inputs:

- publication timestamps
- claim type
- product freshness policy

Base rule:

- score higher when supporting evidence meets the freshness policy for the issue class

Reason codes:

- `fresh_evidence`
- `stale_evidence`

#### `source_quality`

Inputs:

- source tiers
- official-source presence
- paywall and metadata-only limitations

Base rule:

- score higher when higher-tier or official sources materially support the issue

Reason codes:

- `tier_one_or_two_support`
- `official_source_present`
- `low_quality_mix`

#### `explanatory_yield`

Inputs:

- answered open questions
- resolved hypotheses
- distinct transmission paths found

Base rule:

- score higher when enrichment materially improves explainability rather than only adding more similar facts

Reason codes:

- `new_explanatory_signal`
- `little_added_explanation`

#### `counter_view_coverage`

Inputs:

- counter evidence IDs
- falsification contexts
- minority or watch-path support

Base rule:

- score higher when the issue can support both the dominant thesis and a meaningful challenge or falsification path

Reason codes:

- `substantive_counter_view`
- `one_sided_issue`

#### `claimability`

Inputs:

- issue-specific evidence quality
- numeric-check feasibility
- final artifact constraints

Base rule:

- score higher when the issue can be turned into a concise, evidence-grounded brief section without padding

Reason codes:

- `claim_ready`
- `not_claim_ready`

### C. Product Policy Score Features

#### `value_density`

Inputs:

- distinct explanatory signals
- expected brief slot usage
- answered open questions

Base rule:

- score higher when the issue yields more unique explanatory value per brief slot

Reason codes:

- `high_value_density`
- `low_value_density`

#### `coverage_balance`

Inputs:

- support coverage
- counter coverage
- watch or falsification coverage

Base rule:

- score higher when the issue can support balanced brief treatment instead of a one-sided write-up

Reason codes:

- `balanced_issue`
- `imbalanced_issue`

#### `non_redundancy`

Inputs:

- overlap with already selected issues
- redundancy penalty helper

Base rule:

- `non_redundancy = 1 - redundancy_penalty`

Reason codes:

- `distinct_from_selected`
- `high_overlap_with_selected`

#### `brief_fit`

Inputs:

- issue budget
- current selection set
- brief thesis fit

Base rule:

- score higher when the issue fits the brief's limited space and complements already selected issues

Reason codes:

- `fits_brief_budget`
- `redundant_for_brief`
- `weak_fit_for_today_brief`

## 4. PR Split Order

Recommended implementation sequence:

### PR1: Schema + Artifacts

Scope:

- additive tables
- dual-written JSON artifacts
- feature flags and budget config placeholders

### PR2: Event Clustering

Scope:

- canonical-news-item input path
- clustering logic
- event and event-item artifacts

### PR3: Candidate Builder + Scoring

Scope:

- single-event candidates
- multi-event relation mapping
- discovery-score features

### PR4: Selector + Shadow Mode

Scope:

- shortlist logic
- issue enricher wiring
- enrichment score
- shadow-mode output and comparisons

### PR5: Primary Switch

Scope:

- promote selector from `shadow` to `primary`
- keep fallback and comparison hooks during rollout

### PR6: Value Critic

Scope:

- `integrity_critic`
- `value_gate`
- `revision_router`
- final artifact gates

## Out-Of-Scope For This Spec

This spec does not define:

- alert implementation changes
- board/dashboard UX
- long-term cross-run event identity stabilization
- post-V0 model-provider strategy
