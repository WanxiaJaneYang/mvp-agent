# ADR: Market Intelligence Pipeline Redesign

Status: Proposed

Issue anchor: GitHub issue [#193](https://github.com/WanxiaJaneYang/mvp-agent/issues/193)

## Decision

Reframe the repository from a `daily_brief` generation pipeline into a market-intelligence pipeline with brief products on top.

The new architectural spine is explicitly two-speed:

`market_stream -> candidate_builder -> cheap_scoring -> shortlist -> issue_enricher -> rerank/select -> briefing -> critic + hard_gate -> products`

This replaces the old shape where the system effectively does:

`broad evidence pack -> issue selection -> brief assembly`

The new rule is the reverse:

- first select a small set of issues cheaply
- then spend deeper research and composition effort only on those shortlisted issues

## Why This Change

The current repo has improved downstream brief structure:

- issue-centered synthesis
- structured claims
- claim delta and publish-decision plumbing

But upstream discovery is still too corpus-centric. Verified bottlenecks in the current codebase:

- `apps/agent/daily_brief/runner.py`
  - still compresses the day into a token-frequency query
  - still builds broad evidence before issue selection is truly settled
- `apps/agent/daily_brief/editorial_planner.py`
  - still derives candidate issue seeds from token frequency
- `apps/agent/daily_brief/issue_retrieval.py`
  - still buckets `counter`, `minority`, and `watch` through lexical terms
- `apps/agent/daily_brief/critic.py`
  - still behaves mainly like an integrity or shallowness check, not a first-class value gate

That means the repo can now render issue-shaped briefs, but it still discovers those issues from corpus-frequency heuristics. The system still grows a brief from a pile of documents instead of growing selected issues from a market-state view.

## What This ADR Decides

### Two-Speed Architecture

The redesign adopts two execution speeds.

Fast, cheap, mostly deterministic upstream:

- `market_stream`
- `candidate_builder`
- `cheap_scoring`
- `shortlist`

Slow, targeted, more expensive downstream:

- `issue_enricher`
- `rerank/select`
- `briefing`
- `critic + hard_gate`

The first speed should not be LLM-led. It should prefer deterministic or lightweight logic for:

- canonicalizing market/news items
- clustering them into events
- generating issue candidates
- producing a shortlist

The second speed is where research-like behavior is allowed, but only for a small shortlisted set. Research is not the architecture. Research is a bounded enrichment step attached to shortlisted issues.

### Upper-Layer Responsibilities

```text
apps/agent/
  market_stream/
  issue_discovery/
  briefing/
  products/
```

- `market_stream`
  - canonicalize incoming market/news items
  - cluster related coverage into events
  - produce run-level market state artifacts for explainability and framing
- `issue_discovery`
  - build issue candidates from events
  - score candidates cheaply
  - shortlist candidates
  - enrich only shortlisted candidates
  - rerank and select after enrichment
- `briefing`
  - assemble issue-specific evidence
  - compose claims
  - review, route revisions, and gate the final artifact
- `products`
  - render and deliver daily briefs, alerts, and board/dashboard views

Lower-level packages such as `ingest`, `retrieval`, `storage`, and `runtime` remain shared infrastructure.

### Research-Style Capability Boundaries

The redesign does not introduce a repo-wide `Architect / Scout / Writer / Critic` agent system.

Instead, research-style capability is constrained to two places:

- `issue_discovery.issue_enricher`
  - a small orchestrator for shortlisted issues only
- `briefing`
  - structured review, revision routing, and final gating

This keeps research as a bounded issue-enrichment process rather than turning the whole system into a generic research agent.

### Daily Brief Is A Product, Not The Architecture

`daily_brief` should stop owning:

- market discovery
- issue selection
- evidence assembly
- publish logic

Instead, daily brief becomes one consumer of the shared intelligence layer.

`editorial_planner` is explicitly demoted into the product layer. It may only do:

- selected-issue ordering
- brief structure organization
- angle or framing adjustment
- word-budget and section-budget allocation

It must not return to discovery or issue-seed generation.

### Shared Versus Product-Specific Boundaries

Shared across products:

- event model
- issue candidate model
- enrichment model
- review and gating vocabulary where the semantics are truly shared
- score primitives where they are genuinely reusable

Product-specific:

- daily brief
  - issue selection policy
  - issue enrichment depth
  - value-density threshold
  - artifact structure
- alerts
  - event-trigger policy
  - category floors
  - cooldown and daily-cap policy
  - alert-specific evidence floor
- board/dashboard
  - ranking policy
  - operator explainability surfaces
  - visibility thresholds

This ADR explicitly does not require one identical selector across daily brief, alerts, and board consumers. Shared primitives are not the same thing as a shared policy.

### Briefing Boundaries

The briefing layer is explicitly responsible for:

- `evidence_assembler`
- `claim_composer`
- `integrity_critic`
- `value_gate`
- `revision_router`
- `hard_gate`

This ADR decides that review and gating belong inside briefing. It does not lock down the exact Phase 1 contract for those components.

## What This ADR Preserves

This redesign keeps the recent daily-brief work that already improved downstream structure:

- issue-centered brief output
- structured issue-planner and claim-composer contracts
- claim delta and publish-decision contracts

Those remain useful, but they move down the stack into `briefing` and `products` instead of defining the whole repository architecture.

## What This ADR Does Not Decide

This ADR does not lock down:

- exact object contracts
- Phase 1 scoring formulas
- additive schema details
- feature flags or rollout budgets
- evaluation thresholds
- future product expansion beyond the boundary definitions above

Those belong in follow-on design documents, not in the architecture decision itself.

## Consequences

### Positive

- the repo architecture aligns with the real bottleneck: discovery, scoring, and selection
- broad corpus research is replaced by targeted issue enrichment
- daily brief stops being the place where every concern gets coupled
- alerts and board views can share upstream intelligence without inheriting daily-brief internals

### Trade-Offs

- the repo needs new persistent contracts around event, candidate, enrichment, and review state
- some current daily-brief modules will be split or renamed
- migration must stay additive at first because `query_text`, `evidence_packs`, and current evals are still live dependencies

## Explicit Non-Decisions

This ADR is not choosing:

- a universal multi-agent architecture
- a long-form research-report product strategy
- an LLM-first discovery layer
- a single selection policy shared unchanged by all products

## Follow-On Required

After this ADR, the next planning artifact should be a Phase 1 design for `issue discovery v0` that covers:

- object contracts
- two-stage scoring
- additive schema
- feature flag and iteration budgets
- eval and rollout
- success metrics
