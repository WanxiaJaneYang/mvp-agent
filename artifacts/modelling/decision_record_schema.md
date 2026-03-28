# Decision Record Schema v1

Purpose: define a file-first, auditable decision artifact for synthesis outputs.

Status: P0 schema definition artifact.

## 1. Scope

In-scope run types:
- `daily_brief`
- `alert`

Out of scope for this artifact:
- pipeline wiring
- DB persistence
- MCP exposure

## 2. Storage Location

Decision records are stored as JSON files at:

`artifacts/decision_records/<YYYY-MM-DD>/<run_id>.json`

Retention policy: indefinite.

## 3. Top-level Schema

Required top-level fields:

1. `schema_version` (`decision_record.v1`)
2. `record_id` (string, `dr_<id>`)
3. `run_id` (string)
4. `run_type` (enum: `daily_brief`, `alert`)
5. `generated_at_utc` (ISO-8601 UTC)
6. `status` (enum: `ok`, `partial`, `abstained`, `failed`)
7. `claims` (array)
8. `rejected_alternatives` (array)
9. `risk_flags` (array)
10. `budget_snapshot` (object)
11. `guardrail_checks` (object)
12. `artifacts` (object)
13. `decision_rationale` (object)
14. `withheld_claims` (array)
15. `delivery_summary` (object)

Raw prompt/completion payloads are not allowed in v1.

## 4. Nested Objects

### 4.1 `claims[]`

Required fields per claim:
1. `claim_id` (string)
2. `issue_id` (string)
3. `section` (enum: `prevailing`, `counter`, `minority`, `watch`, `changed`)
4. `text` (string)
5. `citation_ids` (array of strings)
6. `coverage_status` (enum: `schema_valid`, `supported`, `unsupported`)
7. `delivery_status` (enum: `delivered`, `withheld`, `issue_abstained`, `brief_abstained`, `removed`)
8. `validator_action` (enum: `kept`, `removed`, `downgraded_internal`, `issue_abstained`, `brief_abstained`)

### 4.1.1 `withheld_claims[]`

Required fields per withheld claim:
1. `claim_id` (string)
2. `issue_id` (string)
3. `reason_code` (enum: `insufficient_evidence`, `cross_issue_leakage`, `placeholder_internal_only`, `brief_abstained`, `issue_abstained`)
4. `delivery_status` (enum: `withheld`, `issue_abstained`, `brief_abstained`, `removed`)

### 4.1.2 `delivery_summary`

Required fields:
1. `delivered_claim_count` (integer)
2. `withheld_claim_count` (integer)
3. `has_withheld_supported_content` (boolean)

### 4.2 `rejected_alternatives[]`

Required fields:
1. `candidate_summary` (string)
2. `reason_code` (enum: `insufficient_evidence`, `policy_violation`, `low_confidence`, `out_of_scope`, `duplicate_narrative`)

Optional:
1. `notes` (string)

### 4.3 `budget_snapshot`

Required fields:
1. `hourly_spend_usd` (number)
2. `hourly_cap_usd` (number)
3. `daily_spend_usd` (number)
4. `daily_cap_usd` (number)
5. `monthly_spend_usd` (number)
6. `monthly_cap_usd` (number)
7. `allowed` (boolean)

### 4.4 `guardrail_checks`

Required fields:
1. `citation_check` (enum: `pass`, `warn`, `fail`)
2. `paywall_check` (enum: `pass`, `warn`, `fail`)
3. `diversity_check` (enum: `pass`, `warn`, `fail`)
4. `budget_check` (enum: `pass`, `warn`, `fail`)
5. `notes` (array of strings)

### 4.5 `artifacts`

Fields:
1. `synthesis_id` (string, optional when status is `failed`)
2. `output_path` (string, optional when status is `failed`)
3. `output_sha256` (string, required if output exists)

### 4.6 `decision_rationale`

Required fields:
1. `summary` (string)
2. `confidence_label` (enum: `high`, `medium`, `low`)
3. `key_drivers` (array of strings)
4. `uncertainties` (array of strings)

## 5. Field-Level Validation Rules

1. `schema_version` must equal `decision_record.v1`.
2. `run_type` must be `daily_brief` or `alert`.
3. `status` must be one of `ok`, `partial`, `abstained`, `failed`.
4. `generated_at_utc` must be parseable ISO-8601 UTC.
5. For every claim with `coverage_status = supported`, `citation_ids` length must be >= 1.
6. If `status = abstained`, `decision_rationale.uncertainties` must be non-empty.
7. `budget_snapshot.allowed` must be false when any spend is >= cap.
8. If `status != failed`, `artifacts.output_sha256` should be present.
9. `guardrail_checks` values must be restricted to `pass|warn|fail`.
10. `claims[].delivery_status = delivered` is required for any claim surfaced to users.
11. `withheld_claims` must capture every claim removed after validation or withheld from delivery.
12. If `status = abstained`, `delivery_summary.has_withheld_supported_content` must indicate whether any internally surviving issue content was held back from delivery.

## 6. Example Reference

Canonical example:

`artifacts/modelling/examples/decision_record_v1.example.json`
