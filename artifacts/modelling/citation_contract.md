# Citation Contract - Evidence Grounding Rules

**Purpose:** Define how every delivered issue, claim, and rendered output must be backed by citations to stored evidence.

**Scope:** Applies to all AI-generated content: daily briefs, major event alerts, synthesis summaries.

---

## 1. Citation Object Format

Every citation references a stored document/chunk with the following structure:

```json
{
  "id": "cite_<uuid>",
  "source_id": "fed_press_releases",
  "publisher": "Federal Reserve",
  "doc_id": "doc_<uuid>",
  "chunk_id": "chunk_<uuid>",
  "url": "https://www.federalreserve.gov/newsevents/pressreleases/...",
  "title": "Federal Reserve announces...",
  "published_at": "2026-02-10T14:00:00Z",
  "fetched_at": "2026-02-11T02:15:00Z",
  "quote_span": {
    "start": 150,
    "end": 320,
    "text": "...actual quoted text snippet..."
  },
  "snippet_span": {
    "text": "...headline or RSS snippet..."
  }
}
```

**Required fields:**
- `id`
- `source_id`
- `publisher`
- `doc_id`
- `url`
- `title`
- `published_at`
- `fetched_at`

**Optional fields:**
- `chunk_id`
- `quote_span`
- `snippet_span`

**Paywall-sourced citations:**
- If `paywall_policy: metadata_only`:
  - citation MUST NOT include `quote_span`
  - citation MAY include `snippet_span`
  - system must NOT fabricate or extract paywalled full text

---

## 2. Structured Output Levels

The system now has three grounding levels:

1. **Issue map**
   - identifies the issue and the evidence sets associated with it
2. **Claim objects**
   - express the prevailing/counter/minority/watch arguments for one issue
3. **Rendered output**
   - HTML/email presentation of issue summaries, claims, and evidence

Citations must remain traceable through all three levels.

---

## 3. Core Grounding Rule

**Absolute requirement:** every delivered claim span must have citation coverage.

This means:
- every `claim_text` must reference one or more valid citation IDs
- every visible evidence item shown under a claim must reference one valid citation ID
- renderer must not surface prose that cannot be mapped back to stored citations

If a claim cannot be cited, it must not appear in the output.

---

## 4. Issue Planner Contract

The issue planner outputs structured JSON, not prose.

Each issue must include evidence pointers similar to:

```json
{
  "issue_id": "issue_growth_rates",
  "issue_question": "Will softer growth change near-term Fed expectations?",
  "thesis_hint": "Growth is cooling, but inflation persistence complicates any near-term policy pivot.",
  "supporting_evidence_ids": ["chunk_1", "chunk_2"],
  "opposing_evidence_ids": ["chunk_3"],
  "minority_evidence_ids": ["chunk_4"],
  "watch_evidence_ids": ["chunk_5"]
}
```

**Validation rules:**
- `issue_question` must be specific enough to anchor a debate
- evidence IDs must resolve to known chunks/documents
- supporting/opposing/minority/watch evidence sets must belong to the same issue context

---

## 5. Claim Composer Contract

The claim composer outputs structured JSON objects instead of direct HTML.

Each claim must include fields similar to:

```json
{
  "claim_id": "claim_growth_prevailing",
  "issue_id": "issue_growth_rates",
  "claim_kind": "prevailing",
  "claim_text": "Most evidence suggests softer activity is increasing pressure for cuts later this year, but not enough to force an immediate pivot.",
  "supporting_citation_ids": ["cite_101", "cite_102"],
  "opposing_citation_ids": ["cite_201"],
  "confidence": "medium",
  "novelty_vs_prior_brief": "strengthened",
  "why_it_matters": "If growth continues to soften without a matching drop in inflation, rate-sensitive assets may stay volatile."
}
```

**Validation rules:**
- every claim has at least one supporting citation
- `counter` and `minority` claims must still reference the same `issue_id`
- `why_it_matters` and `novelty_vs_prior_brief` are also grounded outputs and may be removed if unsupported

---

## 6. Claim-Span Citation Binding

**Goal:** keep the UX readable while enforcing claim-level grounding closer to academic sentence-level citation.

### 6.1 Definitions

- **Claim object:** a structured argument associated with one issue and one claim kind
- **Claim span:** the smallest sentence or clause that asserts a fact, inference, or prediction
- **Evidence item:** a visible supporting item shown under a claim in rendered output

### 6.2 Rule

Every claim span must be covered by one of these patterns:

**A) Sentence-level citation binding (preferred):**
```markdown
Prevailing: Growth indicators softened across recent releases. [1]
Inflation commentary still argues against a rapid pivot. [2]
```

**B) Shared citation binding for a short consecutive span (allowed):**
```markdown
Prevailing: Growth indicators softened while inflation commentary stayed sticky, which supports a later-but-not-immediate cut path. [1][2]
```

**Not allowed:**
- one claim object containing multiple unsupported assertions
- a rendered evidence item without a citation
- support/opposition statements that cannot be mapped to citations

### 6.3 Formatting constraints

- keep claim text concise enough that validation can map spans to citations deterministically
- if support for separate sentences differs, each sentence must carry its own citations
- visible evidence blocks should show source, date, and snippet/quote derived from the citation object

---

## 7. Validator Behavior

Before delivering any synthesis output, the system MUST run a deterministic validator that:

1. extracts all claim objects
2. checks each claim has at least one valid supporting citation
3. verifies each citation resolves to:
   - a valid doc/chunk in local evidence store
   - a URL that matches the source registry entry
   - a non-null `published_at`
4. verifies issue consistency:
   - each claim references a valid `issue_id`
   - `prevailing`, `counter`, and `minority` claims under one issue address the same issue question
5. verifies rendered evidence blocks are backed by cited evidence

**On validation failure:**

| Failure Type | Action |
|--------------|--------|
| Claim has 0 supporting citations | Remove claim or replace with explicit insufficient-evidence language |
| Citation ID not found in store | Remove citation; if no valid citations remain, drop claim |
| Citation missing required fields | Remove citation; if no valid citations remain, drop claim |
| Paywalled source cited with full-text quote | Strip `quote_span`, keep metadata-only citation |
| Claim drift across one issue | Mark issue invalid and retry or abstain |

**Validator output:**

```json
{
  "total_claims": 8,
  "valid_claims": 7,
  "removed_claims": 1,
  "issue_failures": 0,
  "validation_passed": true
}
```

---

## 8. Citation Quality Checks

### Numeric / Time Claims Rule

If a claim contains numbers, percentages, or specific dates (except purely scheduled dates from official calendars), it must satisfy one of:

- at least one Tier 1-2 citation, or
- at least two independent sources

If not, validator must remove or downgrade the claim.

### Policy Claims Rule

If a claim is about central bank policy or official macro releases, and a Tier 1 source exists in the evidence pack:

- require at least one Tier 1 citation

If not, validator must remove or downgrade the claim.

### Novelty / Delta Rule

If `novelty_vs_prior_brief` claims a change such as `strengthened`, `weakened`, or `reversed`, the system must have both:

- prior brief context
- current citations supporting the new state

If not, downgrade `novelty_vs_prior_brief` to `unknown` or remove it.

---

## 9. Critic Pass

An optional critic layer may evaluate claim quality after deterministic validation.

It must not invent or rewrite claims. It can only:
- pass
- warn
- fail

Recommended critic checks:
- is this just source-by-source paraphrase?
- does the counter claim genuinely challenge the prevailing thesis?
- is the minority claim materially distinct?
- is `why_it_matters` specific rather than generic?

Critic output should be structured:

```json
{
  "status": "warn",
  "reason_codes": ["minority_not_distinct"],
  "flagged_claim_ids": ["claim_growth_minority"]
}
```

---

## 10. Retry and Abstain Policy

To prevent runaway costs from repeated synthesis attempts, enforce bounded retries:

- issue planner: max 1 retry
- claim composer: max 1 retry
- validation-triggered composer retry: max 1 retry

If synthesis still fails:
- allow issue-level abstain when one issue is not supportable
- use brief-level abstain when no trustworthy issues remain

**Abstain language examples:**
- `[Insufficient evidence to assess this issue]`
- `[Conflicting reports; unable to confirm a defensible prevailing view]`
- `[No official statement found in available sources]`

---

## 11. Evidence-Pack Definition

The evidence pack remains deterministic and bounded.

### 11.1 Retrieval Constraints

- max chunks per query/run: `30`
- chunk size: 300-500 tokens (configurable)
- recency window: prioritize last 7 days; include up to 30 days for context

### 11.2 Diversity Constraints

- no single publisher >40% of evidence pack
- at least 50% of evidence from Tier 1 or Tier 2 sources
- Tier 4 evidence <=15%
- support issue debates with multiple perspectives when available

### 11.3 Evidence-Pack Metadata

Each evidence pack must store:

```json
{
  "pack_id": "pack_<uuid>",
  "generated_at": "2026-02-11T08:00:00Z",
  "chunks": [
    { "chunk_id": "chunk_<uuid>", "source_id": "fed_press_releases", "score": 0.92, "credibility_tier": 1 }
  ],
  "diversity_stats": {
    "unique_publishers": 8,
    "tier_1_pct": 45,
    "tier_2_pct": 40,
    "tier_3_pct": 10,
    "tier_4_pct": 5,
    "max_publisher_pct": 35
  }
}
```

---

## 12. Paywall Rule

Sources marked `paywall_policy: metadata_only`:
- store title, URL, published timestamp, RSS snippet if available
- do not store or fabricate full-text content
- do not extract content behind login/paywall

When citing a paywalled source:
- allowed: metadata-backed title/snippet-based citation
- not allowed: fabricated quote spans or implied full-text reading

Rendered output should make paywall status visible.

---

## 13. Citation Presentation in Outputs

Renderer should present citations in a readable issue-centered format:

```markdown
## Issue: Will softer growth change near-term Fed expectations?

Summary: Recent growth data softened, but inflation commentary still argues against an immediate pivot.

### Prevailing
Most evidence suggests softer activity raises pressure for cuts later this year, not immediately. [1][2]

Evidence
- Federal Reserve, Mar 10, 2026: "...more confidence..." [1]
- Reuters, Mar 10, 2026: "..." [2]

### Counter
Some analysts argue inflation persistence means rates can stay restrictive for longer. [3]

### Minority
A smaller set of views expects growth weakness to force a faster policy turn. [4]
```

At the end of each output, include a references section with source title, publisher, date, URL, and paywall label when applicable.

---

## 14. Storage Mapping

The system must preserve lineage from rendered output back to evidence:

- `run_id` -> `issue_map`
- `issue_id` -> claim objects
- `claim_id` -> supporting/opposing citation IDs
- rendered evidence items -> citation IDs

This enables validator audits, debugging, and decision-record persistence.

---

## 15. Acceptance Summary

1. No uncited delivered claims
2. Issue planner and claim composer output schema-valid JSON
3. Claims stay grounded in deterministic evidence
4. Renderer never shows unsupported prose
5. Explicit abstention replaces unsupported synthesis
