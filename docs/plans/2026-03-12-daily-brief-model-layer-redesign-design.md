# Daily Brief Model-Layer Redesign

Issue anchor: GitHub issue [#87](https://github.com/WanxiaJaneYang/mvp-agent/issues/87)

## Goal

Redesign the daily-brief pipeline so it produces analyst-style, issue-centered synthesis instead of flat section bullets assembled directly from source titles and snippets.

The new pipeline must:
- keep evidence acquisition and grounding deterministic
- introduce an explicit model-driven issue-planning layer
- introduce an explicit model-driven claim-composition layer
- validate structured claims before rendering
- render from structured analysis objects rather than thin section bullets

## Why The Current Design Is Insufficient

The current vertical slice has a useful deterministic backbone, but its synthesis behavior is still structurally shallow:
- one global query drives one evidence pack
- `build_synthesis(...)` selects one candidate per section
- bullet text is assembled from document title/snippet text rather than multi-source analysis
- stage 8 validates citation compliance, not analytical quality
- renderer consumes thin `section -> bullets` structures with no thesis or claim layer

This makes the output valid enough to demo pipeline wiring, but not good enough to behave like a literature-review brief.

## Design Principles

1. Evidence remains deterministic.
2. Models operate only on bounded, deterministic evidence artifacts.
3. Models return structured JSON, not direct HTML prose.
4. Validation stays local-first and rules-first.
5. Rendering is downstream of issue and claim semantics, not upstream of them.
6. Provider abstraction must be narrow and task-shaped, not a generic “universal LLM framework”.

## Target Pipeline

The daily-brief run becomes:

`deterministic evidence layer -> issue planner -> claim composer -> validator / critic -> renderer -> decision record`

### Stage A: Deterministic Evidence Layer

This stage remains non-model and should preserve the repo's current strengths:
- ingestion
- extraction
- normalization
- deduplication
- chunking
- retrieval
- citation store construction
- budget guard enforcement

Outputs from this stage:
- normalized documents
- chunks / retrieval rows
- citation store
- evidence pack
- run metrics
- optional prior-brief context

This layer must remain deterministic and replayable.

### Stage B: Issue Planner

The issue planner is the first model pass. It does not write prose for end users.

Inputs:
- evidence pack
- citation store summary
- optional prior-brief summary context
- explicit schema contract

Output:
- `IssueMap[]` as JSON

Responsibilities:
- identify 2-3 important issues for the run when supported by evidence
- define one explicit question or thesis per issue
- assign evidence groups to supporting, opposing, minority, and watch buckets
- avoid source-by-source narration

Non-responsibilities:
- no HTML
- no final prose rendering
- no citation validity decisions

### Stage C: Claim Composer

The claim composer is the second model pass. It consumes `IssueMap[]` and writes structured claims.

Inputs:
- issue map
- citation store
- optional prior-brief context
- explicit schema contract

Output:
- `ClaimObject[]` grouped by issue

Responsibilities:
- write issue-centered claims
- articulate `prevailing`, `counter`, `minority`, and `watch` around the same thesis
- explain `why_it_matters`
- classify `novelty_vs_prior_brief`

Non-responsibilities:
- no final HTML
- no citation validation
- no unconstrained free-form writing

### Stage D: Validator / Critic

This stage is split into two layers.

#### D1. Rule Validator

Always deterministic. Must enforce:
- schema validity
- citation coverage
- paywall compliance
- source quality thresholds
- numeric/date claim support strength
- issue consistency

The validator decides whether output is:
- `ok`
- `partial`
- `retry`
- `abstained`

#### D2. Critic Pass

Optional model layer. It does not rewrite the output.

It only flags quality failures such as:
- source-by-source paraphrase disguised as synthesis
- `counter` not actually addressing the same thesis
- `minority` merely restating the dominant view more weakly
- empty or generic `why_it_matters`
- unsupported novelty/delta labels

Output should be structured:
- `pass | warn | fail`
- `reason_codes`
- `flagged_issue_ids`
- `flagged_claim_ids`

### Stage E: Renderer

HTML/email should consume structured issue and claim objects, not thin section bullets.

Renderer responsibilities:
- show issue question
- show issue summary
- show competing argument groups
- show evidence under claims
- show why it matters
- show novelty / change markers

Renderer should not infer issue structure on its own.

### Stage F: Decision Record

Decision record persistence should include:
- issue map
- claim objects
- validator report
- critic report
- rendered artifact path/hash
- abstain / retry rationale

The persisted record should make it possible to inspect how the brief was planned, composed, validated, and delivered.

## Structured Contracts

### IssueMap

```json
{
  "issue_id": "issue_001",
  "issue_question": "Will softer growth meaningfully change near-term Fed expectations?",
  "thesis_hint": "Evidence is split between softer macro data and steady official policy language.",
  "supporting_evidence_ids": ["ev_001", "ev_002"],
  "opposing_evidence_ids": ["ev_003"],
  "minority_evidence_ids": ["ev_004"],
  "watch_evidence_ids": ["ev_005"]
}
```

### ClaimObject

```json
{
  "claim_id": "claim_001",
  "issue_id": "issue_001",
  "claim_kind": "prevailing",
  "claim_text": "The dominant near-term view is that softer growth data is nudging expectations, but not yet enough to override steady Fed messaging.",
  "supporting_citation_ids": ["cite_001", "cite_002"],
  "opposing_citation_ids": ["cite_003"],
  "confidence": "medium",
  "novelty_vs_prior_brief": "strengthened",
  "why_it_matters": "If growth softness starts outweighing policy inertia, rate-sensitive assets could reprice quickly."
}
```

### DailyBriefSynthesisV2

```json
{
  "issues": [
    {
      "issue_id": "issue_001",
      "issue_question": "...",
      "issue_summary": "...",
      "claims": [
        { "claim_id": "claim_001", "claim_kind": "prevailing", "..." : "..." },
        { "claim_id": "claim_002", "claim_kind": "counter", "..." : "..." },
        { "claim_id": "claim_003", "claim_kind": "minority", "..." : "..." },
        { "claim_id": "claim_004", "claim_kind": "watch", "..." : "..." }
      ]
    }
  ],
  "meta": {
    "status": "ok"
  }
}
```

## Provider Strategy

Provider abstraction is provider-agnostic, but implemented first for OpenAI.

The abstraction should be task-specific, not generic:
- `IssuePlannerProvider`
- `ClaimComposerProvider`

Initial concrete adapters:
- `OpenAIIssuePlannerProvider`
- `OpenAIClaimComposerProvider`

Why this shape is preferred:
- narrow interfaces
- fewer abstractions than a full generic LLM framework
- easier schema enforcement
- easier eval across providers later

## Prior Brief / Delta Design

`novelty_vs_prior_brief` must not be inferred in the renderer.

The deterministic layer should provide a bounded prior-brief context package:
- prior issue questions
- prior claim summaries
- prior citation IDs / source IDs
- prior generation timestamp

Allowed novelty labels:
- `new`
- `continued`
- `reframed`
- `weakened`
- `strengthened`
- `reversed`

This lets “what changed since yesterday” emerge from claim-level delta rather than a separate brittle renderer section.

## Failure And Retry Policy

Retries must remain deterministic and bounded.

### Issue planner
- retry once on malformed or empty output
- then abstain

### Claim composer
- retry once on malformed or validator-blocked output
- then abstain

### Rule validator
- may drop or downgrade claims
- may trigger one composer retry
- should not permit unbounded rewrite loops

### Critic
- should not autonomously rewrite
- can downgrade to `partial` or `abstained`
- should flag reasons explicitly

### Abstain behavior

Support two abstain scopes:
- issue-level abstain when one issue is not supportable
- brief-level abstain when no issue survives validation

Abstain output should still use issue-centered structure, not a flat placeholder page.

## Renderer Expectations

The rendered brief should read like a compact analyst memo:
- 2-3 explicit issue questions
- short issue summary
- competing claims organized under the same issue
- evidence attached to the relevant claim
- why-it-matters block
- novelty/change label

The renderer should not directly expose raw source clustering artifacts.

## Validation Expectations

The redesign is considered successful when:
- the pipeline can produce 2-3 issues from one run
- each issue has a single coherent thesis/question
- `prevailing / counter / minority` are about the same issue
- claims are not merely source summaries
- output remains fully grounded and citation-valid
- provider layer remains provider-agnostic
- OpenAI is the first implemented provider

## Out Of Scope For This Redesign

- turning the whole system into an unconstrained multi-agent writing workflow
- giving models authority over retrieval, budget, or citation validity
- replacing deterministic evidence infrastructure with model inference
- finalizing full semantic retrieval in the same change set

Retrieval strengthening is related and important, but should be handled as a parallel or follow-on track.
