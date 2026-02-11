# Modelling Phase Checklist

Status: ✓ = PASSING, ✗ = FAILING, ⧖ = IN PROGRESS

## Core Deliverables

- [✓] **A) source_registry.yaml** — Source definitions with credibility tiers, fetch intervals, paywall policies
- [✗] **B) data_model.md** — SQLite schema (sources/documents/chunks/citations/portfolio/alerts/runs) + FTS plan
- [✗] **C) pipeline.md** — Daily pipeline stages (fetch → extract → normalize → chunk → index → retrieve → synthesize → validate → deliver)
- [✗] **D) citation_contract.md** — Citation format, validation rules, abstain behavior
- [✗] **E) alert_scoring.md** — v1 thresholds, rate limits, bundling policy
- [✗] **F) backlog.json** — Build tickets with acceptance criteria (valid JSON)

## Validation & Testing

- [✗] **G) Citation validator** — Validate every bullet has ≥1 citation
- [✗] **H) Budget guard** — Enforce daily/hourly/monthly caps
- [✗] **I) Eval cases** — At least 10 golden test cases in evals/

## Definition of Done

Modelling phase complete when:
- All items A–F exist and are consistent with PRD + PROJECT_FACTS
- backlog.json validates with acceptance criteria
- Citation validator passes
- Budget guard implemented and enabled by default
