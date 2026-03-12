# Claim Rendering And Delivery Contract

## Problem Statement

`StructuredClaim` already carries `why_it_matters` and `novelty_vs_prior_brief`, but
the current delivery path drops those fields before they reach rendered output or
the persisted decision record.

That means the runtime can produce richer analyst-facing claim objects while the
actual brief still degrades back into thin bullets.

## Current Repo Gaps

- `build_synthesis_from_structured_claims()` only forwards text, citations, and confidence
- HTML issue cards do not render novelty or why-it-matters callouts
- plain-text email content does not include simplified claim framing
- the decision record regenerates claims without preserving the editorial fields

## Claim View Model Contract

The renderer-facing bullet model should preserve these claim-level fields end to end:

- `claim_id`
- `claim_kind`
- `text`
- `citation_ids`
- `confidence_label`
- `why_it_matters`
- `novelty_vs_prior_brief`
- `evidence`

This document also defines the publish gate that consumes those same structured fields.

## Delta Contract

Add a `ClaimDelta` artifact between prior-brief context and changed-section rendering.

Required fields:

- `claim_id`
- `prior_claim_ref`
- `novelty_label`
- `delta_explanation`
- `supporting_prior_overlap`

The renderer must stop inferring change from bullet text diffs. `What Changed` should
be produced from `ClaimDelta[]` plus the current structured claims.

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
- `delivery_mode=html_only` when email should not be sent even if local HTML is still written

## HTML And Email Changes

- HTML bullets show the claim text plus a novelty label when present
- HTML bullets show a `Why it matters` callout below the claim body
- email plain text includes the brief bottom line plus one simplified issue summary
- email summaries carry novelty and why-it-matters text when the fields exist

## Decision Record Changes

- preserve `claim_id` when the rendered synthesis already contains it
- persist `claim_kind`
- persist `why_it_matters`
- persist `novelty_vs_prior_brief`

This keeps editorial semantics available for later diffing, review, and publish-gate logic.

## Rollout Plan

1. extend `DailyBriefBullet`
2. populate the fields in structured synthesis
3. render the fields in HTML and email
4. add claim-level delta generation and render `What Changed` from delta objects
5. split citation status vs analytical quality and gate publication on the combined decision
6. cover the flow with renderer and pipeline tests

## Test Plan

- synthesis bullets retain `claim_id`, `claim_kind`, `why_it_matters`, and `novelty_vs_prior_brief`
- claim deltas preserve prior matches and novelty labels
- changed-section rendering comes from `ClaimDelta[]` instead of text diff
- rendered HTML shows novelty labels and why-it-matters callouts
- email plain text includes simplified novelty plus why-it-matters lines
- decision records preserve the claim editorial fields
- critic fail blocks email publication and records `publish_decision=hold`
