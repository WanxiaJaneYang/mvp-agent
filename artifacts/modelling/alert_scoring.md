# Alert Scoring v1

Purpose: define deterministic alert scoring, thresholds, and suppression/bundling rules for major-event alerts.

Status: Modelling deliverable E (`alert_scoring.md`).

## 1. Eligible Alert Categories

- `policy`: central bank statement/minutes/speech/press release (Tier 1 preferred).
- `macro_release`: major official prints (CPI/jobs/GDP and similar Tier 1 releases).
- `corporate_event`: material SEC 8-K / major IR events for index-relevant names or watchlist.
- `narrative_shift`: topic-distribution contradiction vs trailing 7-day baseline (Tier 2+ support required).

## 2. Scoring Components (0-100 each)

- `importance`: objective market significance of event type.
- `evidence_strength`: source quality, source diversity, and citation completeness.
- `confidence`: extraction + classification confidence and consistency.
- `portfolio_relevance`: overlap with user holdings/watchlist and broad-market exposure.
- `noise_risk`: rumor/duplicate/low-quality amplification risk.

## 3. Composite Score

Use weighted score:

`total = 0.30*importance + 0.25*evidence_strength + 0.20*confidence + 0.15*portfolio_relevance - 0.10*noise_risk`

Clamp total to `[0, 100]`.

## 4. Minimum Gate Rules (must pass before threshold check)

- At least one Tier 1 or two independent Tier 2 sources.
- At least one valid citation per alert bullet.
- Publisher share in evidence pack <= 40% from one publisher.
- Tier mix in evidence pack: >=50% Tier 1/2 and <=15% Tier 4.
- Paywall policy respected (metadata-only sources never used as fabricated full text).

If any gate fails: do not alert; emit suppression reason.

## 5. Threshold Policy

- `total >= 70`: send immediate alert (if rate-limit policy allows).
- `55 <= total < 70`: do not send immediately; bundle into next daily brief "what changed" or watch section.
- `total < 55`: suppress and log.

Category floor overrides:
- `policy` and `macro_release`: require `importance >= 60`.
- `corporate_event`: require `importance >= 55` and `portfolio_relevance >= 35`.
- `narrative_shift`: require `evidence_strength >= 60` and `confidence >= 55`.

## 6. Rate Limiting and Suppression

- Max alerts/day: `3`.
- Cooldown between alerts: `60` minutes.
- If cooldown active: suppress and queue summary candidate for daily brief.
- If daily cap reached: suppress and queue summary candidate.

Suppression reasons (stored):
- `below_threshold`
- `failed_quality_gate`
- `cooldown_active`
- `daily_cap_reached`
- `budget_stopped`

## 7. Bundling Rules

When immediate send is blocked or below immediate threshold but still notable:
- Include up to 3 bundled items in next daily brief.
- For each bundled item include:
  - 1-2 bullets
  - why it matters
  - what to watch next
  - citations
- Deduplicate bundled items by topic and issuer/publisher cluster.

## 8. Alert Output Constraints

- Max length: about 400 words.
- Structure: 3-6 bullets + "why it matters" + "what to watch next".
- Tone: calm, evidence-led, no trade instructions.

## 9. Calibration Notes (v1)

- Start with conservative threshold (`70`) to minimize noise.
- Recalibrate monthly using false-positive/false-negative review over stored runs.
- Any threshold changes must be logged in progress and reflected in PRD if product behavior changes.
