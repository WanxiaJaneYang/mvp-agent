# ADR: Market Intelligence Pipeline Redesign

Status: Proposed

Issue anchor: GitHub issue [#193](https://github.com/WanxiaJaneYang/mvp-agent/issues/193)

## Decision

Reframe the repository from a `daily_brief` generation pipeline into a market-intelligence pipeline with brief products on top.

The architectural center should become:

`ingest / retrieval / storage -> market_stream -> issue_discovery -> briefing -> products`

not:

`daily_brief runner -> corpus query -> evidence pack -> issue plan -> render`

## Why This Change

The current repo has improved the downstream brief contract:

- issue-centered synthesis
- structured claims
- critic and publish-decision plumbing

But the upstream discovery model is still too corpus-centric. Verified bottlenecks in the current codebase:

- `apps/agent/daily_brief/runner.py`
  - still compresses the day into a token-frequency query
  - still builds one broad evidence pack before issue selection is truly settled
- `apps/agent/daily_brief/editorial_planner.py`
  - still derives candidate issue seeds from token frequency
- `apps/agent/daily_brief/issue_retrieval.py`
  - still buckets `counter`, `minority`, and `watch` through lexical term lists
- `apps/agent/daily_brief/critic.py`
  - still focuses on integrity and shallowness, not a first-class value gate

That means the repo can now render issue-shaped briefs, but it still discovers those issues from corpus-frequency heuristics. The system still grows a brief from a pile of documents instead of growing selected issues from a market-state view.

## What This ADR Decides

### Target Architecture

The repo should be organized around four upper-layer responsibilities:

```text
apps/agent/
  market_stream/
  issue_discovery/
  briefing/
  products/
```

Responsibilities:

- `market_stream`
  - canonicalize incoming market/news items
  - cluster related coverage into events
  - build run-level market snapshots for explainability and framing
- `issue_discovery`
  - build issue candidates from events
  - score, compare, and select candidates
- `briefing`
  - assemble issue-anchored evidence
  - compose claims
  - apply integrity and value gating
- `products`
  - render and deliver user-facing outputs such as daily briefs, alerts, and board/dashboard views

Lower-level packages such as `ingest`, `retrieval`, `storage`, and `runtime` remain shared infrastructure.

### Daily Brief Is A Product, Not The Architecture

`daily_brief` should stop owning all of:

- market discovery
- issue selection
- evidence assembly
- publication logic

Instead, daily brief becomes one consumer of the shared intelligence layer.

### Shared Versus Product-Specific Boundaries

Shared across products:

- event model
- issue candidate model
- score primitives where the semantics are actually shared
- evidence-grounding rules
- value and integrity vocabulary where it applies across consumers

Product-specific:

- daily brief
  - issue selection policy
  - issue enrichment depth
  - publication format and value threshold
- alerts
  - event trigger policy
  - category floors
  - cooldown and daily-cap policy
  - alert-specific evidence gate
- board/dashboard
  - ranking and visibility policy
  - operator explainability views

This ADR explicitly does not require one identical selector across daily brief, alerts, and board consumers.

## What This ADR Preserves

This redesign keeps the recent daily-brief work that already improved downstream structure:

- issue-centered brief output
- structured issue planner and claim composer contracts
- editorial planner as a downstream product-shaping layer
- claim delta and publish-decision contracts

Those remain valid, but they move down the stack into `briefing` and `products` instead of defining the whole repository architecture.

## What This ADR Does Not Decide

This ADR does not lock down:

- exact object contracts
- scoring formula details
- additive schema details
- feature flags
- Phase 1 rollout mechanics
- future product expansion beyond the boundary definitions above

Those belong in follow-on design documents, not in the architecture decision itself.

## Consequences

### Positive

- the repo architecture aligns with the real bottleneck: discovery, scoring, and selection
- daily brief stops being the place where every concern gets coupled
- alerts and board views can share upstream event intelligence without inheriting daily-brief internals
- future refactors can happen layer by layer instead of inside one oversized runner

### Trade-Offs

- implementation will require new persistent contracts around event and issue discovery
- some current daily-brief modules will be split or renamed
- migration must be additive at first because `query_text`, `evidence_packs`, and current evals are still live dependencies

## Explicit Non-Decisions

This ADR is not choosing:

- a universal multi-agent architecture
- a long-form research-report product strategy
- an LLM-first discovery layer
- a single selector policy shared unchanged by all products

## Follow-On Required

After this ADR, the next planning artifact should be a Phase 1 design for `issue discovery v0` that covers:

- object contracts
- scoring formula
- additive schema
- feature flag
- eval and rollout
- success metrics
