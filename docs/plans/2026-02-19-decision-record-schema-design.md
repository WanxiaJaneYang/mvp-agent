# Decision Record Schema Design

**Date:** 2026-02-19  
**Status:** Approved for implementation planning  
**Scope:** P0 schema definition only (file-first storage, no pipeline wiring yet)

## Goal

Define a durable, local-first `decision_record` artifact contract that captures why a `daily_brief` or `alert` output was produced, what evidence supported it, what alternatives were rejected, and what guardrails were checked.

## Constraints

1. Storage must be file-first.
2. Retention is indefinite.
3. In-scope run types: `daily_brief`, `alert`.
4. No raw prompt/completion text in records.
5. Must align with PRD/PROJECT_FACT non-negotiables:
   - citation grounding
   - paywall safety
   - budget hard-stop traceability

## Storage Design

### Path

`artifacts/decision_records/<YYYY-MM-DD>/<run_id>.json`

### Rationale

1. Date-partitioned folders keep local browsing manageable.
2. `run_id` filename gives deterministic linkage to runtime and future DB references.
3. Easy archival and future batch indexing for retrieval/memory tasks.

## Schema Design (v1)

### Top-level required fields

1. `schema_version` (string, fixed: `decision_record.v1`)
2. `record_id` (string, stable ID: `dr_<uuid>`)
3. `run_id` (string, must map to run context)
4. `run_type` (enum: `daily_brief`, `alert`)
5. `generated_at_utc` (ISO-8601 UTC string)
6. `status` (enum: `ok`, `partial`, `abstained`, `failed`)
7. `claims` (array)
8. `rejected_alternatives` (array)
9. `risk_flags` (array)
10. `budget_snapshot` (object)
11. `guardrail_checks` (object)
12. `artifacts` (object)
13. `decision_rationale` (object)

### Claim object

Each `claims[]` item:
1. `claim_id` (string)
2. `section` (enum: `prevailing`, `counter`, `minority`, `watch`, `changed`)
3. `text` (string)
4. `citation_ids` (array of strings)
5. `coverage_status` (enum: `supported`, `insufficient_evidence`, `removed`)

### Rejected alternative object

Each `rejected_alternatives[]` item:
1. `candidate_summary` (string)
2. `reason_code` (enum: `insufficient_evidence`, `policy_violation`, `low_confidence`, `out_of_scope`, `duplicate_narrative`)
3. `notes` (string, optional)

### Budget snapshot object

1. `hourly_spend_usd` (number)
2. `hourly_cap_usd` (number)
3. `daily_spend_usd` (number)
4. `daily_cap_usd` (number)
5. `monthly_spend_usd` (number)
6. `monthly_cap_usd` (number)
7. `allowed` (boolean)

### Guardrail checks object

1. `citation_check` (enum: `pass`, `warn`, `fail`)
2. `paywall_check` (enum: `pass`, `warn`, `fail`)
3. `diversity_check` (enum: `pass`, `warn`, `fail`)
4. `budget_check` (enum: `pass`, `warn`, `fail`)
5. `notes` (array of strings)

### Artifacts object

1. `synthesis_id` (string, optional until full runtime wiring)
2. `output_path` (string, optional)
3. `output_sha256` (string, required if output exists)

### Decision rationale object

1. `summary` (string, concise final reasoning)
2. `confidence_label` (enum: `high`, `medium`, `low`)
3. `key_drivers` (array of strings)
4. `uncertainties` (array of strings)

## Validation Rules

1. `run_type` must be `daily_brief` or `alert`.
2. `generated_at_utc` must be valid UTC ISO-8601.
3. If `status` is `ok` or `partial`, each claim with `coverage_status = supported` must have `len(citation_ids) >= 1`.
4. If `status = abstained`, `decision_rationale.uncertainties` must be non-empty.
5. `budget_snapshot.allowed` must be `false` if any spend >= cap.
6. No raw prompt/completion fields are allowed in schema v1.
7. Any paywall-sensitive claim must reference citation IDs whose source handling remains metadata-safe (enforced by upstream validator, echoed here via `paywall_check`).

## Example JSON (v1)

```json
{
  "schema_version": "decision_record.v1",
  "record_id": "dr_01K2NEXAMPLE9T6H1Y5X4",
  "run_id": "run_01K2NEXAMPLE8J3D4Q2C1",
  "run_type": "daily_brief",
  "generated_at_utc": "2026-02-19T12:35:00Z",
  "status": "partial",
  "claims": [
    {
      "claim_id": "c_prev_001",
      "section": "prevailing",
      "text": "Policy-sensitive sectors remain volatile after the latest central bank hold.",
      "citation_ids": ["cite_001", "cite_014"],
      "coverage_status": "supported"
    },
    {
      "claim_id": "c_watch_002",
      "section": "watch",
      "text": "[Insufficient evidence to support this claim]",
      "citation_ids": [],
      "coverage_status": "insufficient_evidence"
    }
  ],
  "rejected_alternatives": [
    {
      "candidate_summary": "Immediate disinflation trend confirmation",
      "reason_code": "insufficient_evidence",
      "notes": "Conflicting source coverage across tiers."
    }
  ],
  "risk_flags": [
    "macro_release_volatility",
    "policy_uncertainty"
  ],
  "budget_snapshot": {
    "hourly_spend_usd": 0.07,
    "hourly_cap_usd": 0.10,
    "daily_spend_usd": 1.42,
    "daily_cap_usd": 3.00,
    "monthly_spend_usd": 27.31,
    "monthly_cap_usd": 100.00,
    "allowed": true
  },
  "guardrail_checks": {
    "citation_check": "warn",
    "paywall_check": "pass",
    "diversity_check": "pass",
    "budget_check": "pass",
    "notes": [
      "1 claim replaced with insufficient evidence placeholder."
    ]
  },
  "artifacts": {
    "synthesis_id": "syn_01K2NEXAMPLE7B6A5P4Z3",
    "output_path": "artifacts/daily/2026-02-19/brief.html",
    "output_sha256": "9f77f572c4f3c8c4e2f8f8592df1d6f0f2f6a8a3cfd2d0e8c9d8f7a6b5c4d3e2"
  },
  "decision_rationale": {
    "summary": "Delivered partial brief with explicit abstention where evidence quality was insufficient.",
    "confidence_label": "medium",
    "key_drivers": [
      "tier-1 policy releases",
      "broadly corroborated macro commentary"
    ],
    "uncertainties": [
      "mixed near-term labor signal interpretation"
    ]
  }
}
```

## Error Handling

1. Schema mismatch: fail write and mark run `failed` with field-level error.
2. Missing required citation support in supported claims: downgrade to `partial` or `abstained` before write.
3. Missing output artifact hash/path: allow write with artifact fields null only when run status is `failed`.

## Testing Plan (for implementation phase)

1. Unit tests for field presence, enum validation, and required conditional rules.
2. Golden fixture tests for one valid `daily_brief`, one valid `alert`, one abstained record, one invalid record.
3. Path generation tests for date/run_id storage location.

## Out of Scope (this P0 schema task)

1. Runtime generation/wiring in pipeline stages.
2. SQLite persistence of decision records.
3. MCP exposure of decision record resources.
