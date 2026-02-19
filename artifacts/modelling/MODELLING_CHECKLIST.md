# Modelling Phase Checklist

Status: `PASSING`, `FAILING`, `IN_PROGRESS`

## Core Deliverables

- [PASSING] **A) source_registry.yaml** - Source definitions with credibility tiers, fetch intervals, paywall policies
- [PASSING] **B) data_model.md** - SQLite schema (sources/documents/chunks/citations/portfolio/alerts/runs) + FTS plan
- [PASSING] **C) pipeline.md** - Daily pipeline stages (fetch -> extract -> normalize -> chunk -> index -> retrieve -> synthesize -> validate -> deliver)
- [PASSING] **D) citation_contract.md** - Citation format, validation rules, abstain behavior
- [PASSING] **E) alert_scoring.md** - v1 thresholds, rate limits, bundling policy
- [PASSING] **F) backlog.json** - Build tickets with acceptance criteria (valid JSON)

## Validation & Testing

- [PASSING] **G) Citation validator** - Validate every bullet has >=1 citation
- [PASSING] **H) Budget guard** - Enforce daily/hourly/monthly caps
- [PASSING] **I) Eval cases** - At least 10 golden test cases in `evals/`

## Definition of Done

Modelling phase complete when:
- All items A-F exist and are consistent with PRD + PROJECT_FACTS
- `backlog.json` validates with acceptance criteria
- Citation validator passes
- Budget guard implemented and enabled by default
