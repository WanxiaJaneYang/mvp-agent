# Claim Delta, Delivery Fields, and Publish Gate Design

## Problem Statement

The current daily-brief runtime already produces structured claims, but several product-critical fields still stop short of the final output contract:

- `why_it_matters` and `novelty_vs_prior_brief` exist on `StructuredClaim` but can disappear before delivery and persistence.
- the changed section has historically been a renderer-side text diff rather than a claim-level delta object.
- the critic can warn or fail, but it has not been treated as a first-class publish gate with split analytical vs citation status.

This design closes those gaps and makes delivery, decision records, and publication decisions consume the same structured objects the model layer emits.

## Current Repo Gaps

- delivery can flatten claims into thin bullets unless the fields are preserved explicitly
- changed output can be inferred from text changes instead of explicit novelty semantics
- a single `Validated` label hides the distinction between citation validity and analytical quality
- decision records and runtime storage are stronger when these fields are preserved as native claim-level data

## Claim View Model Contract

Renderer-facing bullets should preserve the analytical fields that the model layer already generated.

Example:

```json
{
  "claim_id": "claim_001",
  "claim_kind": "prevailing",
  "text": "Softer growth is raising later-cut expectations.",
  "citation_ids": ["cite_001", "cite_002"],
  "confidence_label": "medium",
  "novelty_vs_prior_brief": "strengthened",
  "why_it_matters": "Rate-sensitive assets can reprice quickly.",
  "delta_explanation": "The same thesis now has additional official support.",
  "evidence": [
    {
      "citation_id": "cite_001",
      "publisher": "Reuters",
      "published_at": "2026-03-12T08:00:00Z",
      "support_text": "Growth data softened again."
    }
  ]
}
```

Required end-to-end surfaces:

- HTML issue cards
- email plain-text summary and HTML alternative
- decision record claims
- runtime artifact JSON

## Delta Contract

Changed output should be derived from `ClaimDelta[]`, not from a bullet text diff.

Example:

```json
{
  "claim_id": "claim_001",
  "prior_claim_ref": "prior_claim_008",
  "novelty_label": "strengthened",
  "delta_explanation": "The same soft-landing thesis now has additional official support.",
  "supporting_prior_overlap": {
    "citation_overlap": 0.33,
    "thesis_overlap": "medium"
  }
}
```

Policy:

- `new`, `reframed`, `weakened`, `strengthened`, and `reversed` appear in `What changed`
- `continued` stays on the issue card but does not need to occupy changed-section space
- the renderer reads `delta_explanation`; it does not infer changed state by comparing old bullet text

## Critic / Publish Decision Contract

Publication should consume a first-class decision object:

```json
{
  "citation_status": "ok",
  "analytical_status": "warn",
  "publish_decision": "publish",
  "reason_codes": ["source_by_source_paraphrase"],
  "delivery_mode": "html_only"
}
```

Policy:

- `citation_status` comes from stage-8 validation and abstain policy
- `analytical_status` comes from the critic
- `publish_decision=hold` when citation status is abstained or analytical status is fail
- `delivery_mode=html_only` when email should not be sent even if artifacts are still written locally

## HTML and Email Rendering Changes

HTML:

- top metadata bar shows `Citation status`, `Analytical quality`, and `Publish decision`
- first screen shows `Bottom line` and `Key takeaways`
- issue bullets render novelty and `Why it matters`
- `What changed` renders delta-driven bullets with `Delta` explanations

Email:

- subject line reflects hold/partial/warn states
- plain-text body includes split statuses, bottom line, top takeaways, and at least one claim with novelty plus `Why it matters`
- HTML alternative remains the full report

## Decision Record Changes

Decision records should preserve:

- `citation_status`
- `analytical_status`
- `publish_decision`
- `reason_codes`
- claim-level `why_it_matters`
- claim-level `novelty_vs_prior_brief`

This keeps delivery decisions auditable without reconstructing intent from rendered HTML.

## Failure Policy

- citation abstain: hold publication
- critic fail: hold publication
- citation partial plus critic pass/warn: publish local artifact, downgrade email delivery to `html_only`
- missing output artifact hash: keep existing downgrade-to-failed behavior

## Rollout Plan

1. Preserve claim fields in synthesis output and renderer.
2. Add `ClaimDelta` generation and switch changed rendering to delta-driven output.
3. Split publish statuses and enforce critic-aware publish gating.
4. Persist the new fields in decision records and runtime artifacts.
5. Add golden evals and delivery tests for missing `why_it_matters`, unsupported novelty, and pseudo-analysis.

## Test Plan

- unit tests for `ClaimDelta` generation and changed-section rendering
- delivery tests for HTML/email rendering of novelty and `Why it matters`
- decision-record tests for split statuses and preserved claim metadata
- runner tests for publish gating and changed-section artifacts
