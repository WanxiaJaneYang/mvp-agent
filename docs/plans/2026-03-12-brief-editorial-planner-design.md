# Brief Editorial Planner, Corpus-First Retrieval, and Issue Quality Gate Design

## Problem Statement

The current daily-brief architecture still starts too close to issue generation. It can identify issue-shaped outputs, but it does not first decide what the brief is trying to say as a whole, how many issue slots the day deserves, or what should happen when the source mix is too thin to justify 2-3 distinct issues.

That creates three recurring failures:
- the day gets compressed into one global query before the system knows the actual editorial thesis
- multiple issues can end up sharing the same evidence base and restating one thesis in slightly different wording
- source-scarce days have no explicit product rule, so the system is incentivized to pad out issue count instead of compressing the brief

This design adds an editorial layer before `IssueMap` generation and makes issue count a deliberate contract instead of an accidental by-product of retrieval.

## Current Repo Gaps

Current gaps in the runtime and product contract are:
- no brief-level `BriefPlan` object before issue planning
- retrieval still centers on a single brief-wide query rather than a corpus-first, issue-aware flow
- no deterministic overlap scoring or information-gain gate between issue planning and final issue selection
- no source-scarcity contract defining when the brief should compress to one main issue

Issue `#135` adds the product contract in `artifacts/PRD.md`. This document defines the technical shape that will later support `#128`, `#129`, and `#130`.

## Target Pipeline

The target upstream daily-brief flow becomes:

1. **Corpus prep**
   - Build a bounded `BriefCorpus` from the day's eligible chunks.
   - Keep recency, credibility, and diversity constraints.
   - Avoid single-publisher dominance before issue planning starts.
2. **Brief planning**
   - Consume `BriefCorpus` summary, prior-brief context, and source-diversity stats.
   - Produce `BriefPlan` with:
     - brief thesis
     - top takeaways
     - issue budget
     - render mode (`full` or `compressed`)
     - candidate issue seeds
     - watchlist
3. **Issue-aware retrieval**
   - For each candidate issue seed, create an `IssueEvidenceScope`.
   - Separate supporting, opposing, minority, and watch evidence.
4. **Issue planning**
   - Generate `IssueMap[]` from `BriefPlan` plus `IssueEvidenceScope[]`.
5. **Editorial quality gate**
   - Run overlap scoring, merge/drop decisions, and minimum information-gain checks.
   - Enforce the final issue budget.
6. **Claim composition and downstream rendering**
   - Out of scope for this document, but downstream layers consume the deduplicated issue set and the chosen render mode.

## BriefCorpus Contract

`BriefCorpus` is the deterministic, auditable input to the editorial planner. It is not a single query result and not yet an `IssueMap`.

Example shape:

```json
{
  "brief_id": "brief_2026-03-12",
  "chunk_ids": ["chunk_01", "chunk_02", "chunk_07"],
  "source_diversity": {
    "unique_publishers": 5,
    "source_roles": ["official", "wire", "market_media"],
    "tier12_ratio": 0.8,
    "dominant_publisher_ratio": 0.25,
    "time_span_hours": 18
  },
  "corpus_summary": [
    "Growth-sensitive data softened.",
    "Policy language remained cautious.",
    "Market pricing moved faster than official guidance."
  ]
}
```

Design intent:
- retrieval happens first at the corpus level, not through one synthesized query string
- corpus prep should retain enough diversity metadata for source-scarcity and issue-budget decisions
- corpus prep can stay deterministic even if later retrieval ranking uses semantic features

## BriefPlan Contract

`BriefPlan` is the editorial contract for the whole brief. It decides the shape of the output before issue generation.

Example shape:

```json
{
  "brief_id": "brief_2026-03-12",
  "brief_thesis": "Softening macro data is widening the gap between market easing expectations and still-cautious policy language.",
  "top_takeaways": [
    "Growth is cooling, but not collapsing.",
    "The market-policy gap widened more than the policy stance itself changed.",
    "The next inflation-sensitive release matters more than today's headline churn."
  ],
  "issue_budget": 2,
  "render_mode": "full",
  "source_scarcity_mode": "normal",
  "candidate_issue_seeds": [
    "growth cooling signal",
    "policy-market gap"
  ],
  "issue_order": [
    "seed_001",
    "seed_002"
  ],
  "watchlist": [
    "next payroll revision",
    "next CPI print"
  ],
  "reason_codes": [
    "two_distinct_debates_supported",
    "third_issue_below_information_gain_threshold"
  ]
}
```

Required fields:
- `brief_thesis`: the main editorial claim for the whole brief
- `top_takeaways`: what belongs above the issue list on first screen
- `issue_budget`: final number of issue slots available to the brief
- `render_mode`: `full` or `compressed`
- `source_scarcity_mode`: explains why the brief stayed full or compressed
- `candidate_issue_seeds`: the issues retrieval and issue planning should investigate
- `watchlist`: items that matter but do not justify a full issue block

Rules:
- default target is 2 issues
- 3 issues require clear incremental value from the third issue
- 1 issue is valid when source scarcity or overlap prevents 2 distinct issue blocks
- `compressed` mode is a product decision, not an error path

## IssueEvidenceScope Contract

Each candidate issue gets its own evidence scope. Final issues must not all reuse one shared evidence pack.

Example shape:

```json
{
  "issue_id": "issue_001",
  "primary_chunk_ids": ["chunk_01", "chunk_07"],
  "opposing_chunk_ids": ["chunk_11"],
  "minority_chunk_ids": ["chunk_15"],
  "watch_chunk_ids": ["chunk_20"],
  "coverage_summary": {
    "unique_publishers": 4,
    "source_roles": ["official", "market_media"],
    "time_span_hours": 18
  }
}
```

Design intent:
- supporting and opposing material should be explicit, not inferred late from one blended pack
- each issue should expose enough coverage metadata to justify its slot in the budget
- a low-coverage issue can still survive as a watch item or takeaway, but not necessarily as a full issue block

## IssueOverlapReport Contract

After `IssueMap[]` generation, the system needs a deterministic overlap report before claims are composed.

Example shape:

```json
{
  "left_issue_id": "issue_001",
  "right_issue_id": "issue_002",
  "question_token_overlap": 0.71,
  "citation_overlap": 0.75,
  "source_overlap": 0.8,
  "thesis_overlap": "high",
  "decision": "merge",
  "reason_codes": [
    "high_citation_overlap",
    "same_underlying_thesis"
  ]
}
```

Initial overlap signals should stay deterministic:
- question token overlap
- citation overlap ratio
- publisher / source-role overlap
- thesis-hint lexical overlap

Decisions:
- `keep`: issues are sufficiently distinct
- `merge`: issues are really one thesis with redundant evidence
- `drop`: lower-value issue adds too little beyond a stronger neighbor

## Information-Gain Policy

Issue count should be limited by incremental value, not by how many candidate issues a planner can produce.

Each issue should receive an `information_gain_score` and a decision:

```json
{
  "issue_id": "issue_002",
  "information_gain_score": 0.18,
  "decision": "drop",
  "reason_codes": [
    "low_incremental_value",
    "restates_existing_issue"
  ]
}
```

First-pass policy:
- compute information gain after overlap scoring, not before
- compare each issue against higher-priority issues already kept in the brief
- penalize:
  - shared citations
  - shared publishers and source roles
  - near-duplicate thesis wording
  - summaries that add no new implication for the reader
- reward:
  - independent source support
  - distinct causal or market implications
  - genuinely new watch items or uncertainty framing

Budget enforcement:
- keep filling issue slots in priority order until `issue_budget` is reached
- the third issue is optional and should be dropped by default unless it clears both overlap and information-gain gates
- when only one issue clears the gate, switch to `compressed` mode instead of manufacturing a weak second issue

## Source-Scarcity Policy

Source scarcity is a normal runtime condition, not an exceptional failure.

Definitions:
- `normal`: the corpus supports at least 2 distinct issues with adequate diversity
- `scarce`: only 1 issue clearly clears the issue-quality gate, or source diversity is too thin for a second issue

Rendering policy:
- `normal` -> `render_mode=full`
  - show `bottom_line`
  - show 2-3 key takeaways
  - show 2 issues by default, 3 only when justified
- `scarce` -> `render_mode=compressed`
  - show `bottom_line`
  - show 2-3 key takeaways
  - show 1 main issue
  - move secondary signals into `watchlist`

Editorial policy:
- do not create a second or third issue only to satisfy a nominal target
- if a candidate issue mostly repeats the main thesis, merge or demote it
- if coverage is too thin for a real debate, keep the insight as a takeaway or watch item
- compressed briefs are acceptable output as long as citation rules still hold

## Rollout Plan

1. Land the product contract in `artifacts/PRD.md`.
2. Add typed `BriefPlan`, `IssueEvidenceScope`, overlap-report, and information-gain contracts.
3. Refactor runner orchestration so stages become:
   - corpus prep
   - brief planning
   - issue-aware retrieval
   - issue planning
   - dedup / information gain
4. Update renderer requirements to respect `full` vs `compressed` brief modes.
5. Add tests and golden cases for source scarcity, issue overlap, and issue-budget enforcement.

This document intentionally does not prescribe provider behavior, claim-level delta, or delivery status gates. Those belong in separate follow-on designs.

## Test Plan

Minimum coverage for the later implementation:
- unit tests for `BriefPlan` generation
  - source-rich corpus -> `render_mode=full`, `issue_budget=2` or `3`
  - source-scarce corpus -> `render_mode=compressed`, `issue_budget=1`
- retrieval tests for issue-aware evidence scopes
  - 2 candidate issues receive materially different scope assignments
  - coverage summaries reflect publisher and source-role diversity
- dedup tests
  - high-overlap issues merge
  - low-information-gain issues drop
  - the third issue is rejected when it adds too little new information
- renderer-facing contract tests
  - compressed brief includes thesis, takeaways, 1 issue, and watchlist
  - full brief does not exceed the approved issue budget

Acceptance outcome:
- the system behaves like an editor choosing the right number of issues for the day, not like a template trying to fill fixed slots.
