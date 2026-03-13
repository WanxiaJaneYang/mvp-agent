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

This PR only adds the claim rendering contract. Later work can extend the same view
model with delta-specific fields without replacing the contract again.

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
4. persist the fields in the decision record
5. cover the flow with renderer and pipeline tests

## Test Plan

- synthesis bullets retain `claim_id`, `claim_kind`, `why_it_matters`, and `novelty_vs_prior_brief`
- rendered HTML shows novelty labels and why-it-matters callouts
- email plain text includes simplified novelty plus why-it-matters lines
- decision records preserve the claim editorial fields
