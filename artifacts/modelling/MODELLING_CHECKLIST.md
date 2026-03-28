# Modelling Phase Checklist

Status: `PASSING`, `FAILING`, `IN_PROGRESS`

## Core Deliverables

- [PASSING] **A) source_registry.yaml** - Source definitions with credibility tiers, fetch intervals, paywall policies
- [PASSING] **B) data_model.md** - SQLite schema (sources/documents/chunks/citations/portfolio/alerts/runs) + FTS plan
- [PASSING] **C) pipeline.md** - Daily pipeline stages (fetch -> extract -> normalize -> chunk -> index -> evidence build -> issue plan -> claim compose -> validate -> deliver)
- [PASSING] **D) citation_contract.md** - Citation format, issue/claim grounding rules, abstain behavior
- [PASSING] **E) alert_scoring.md** - v1 thresholds, rate limits, bundling policy
- [PASSING] **F) backlog.json** - Build tickets with acceptance criteria (valid JSON)

## Validation & Testing

- [PASSING] **G) Citation validator** - Validate every delivered claim has citation coverage
- [PASSING] **H) Budget guard** - Enforce daily/hourly/monthly caps
- [PASSING] **I) Eval cases** - At least 10 golden test cases in `evals/`

## Definition of Done

Modelling phase complete when:
- All items A-F exist and are consistent with PRD + PROJECT_FACTS
- `backlog.json` validates with acceptance criteria
- Citation validator passes
- Budget guard implemented and enabled by default

Canonical runtime status view:
- `docs/status-matrix.md` is the single modelled/coded/verified matrix for current repo state.

## Strengthening Tracks (Prophet Benchmark Review - 2026-02-19)

- [PASSING] **S1) Decision record schema** - Define persisted per-run rationale artifact (claims, citations, rejected alternatives, risk flags, budget usage)
- [FAILING] **S2) Retrieval memory for validated outputs** - Add embedding + retrieval flow for approved historical syntheses
- [FAILING] **S3) Role-lane orchestration** - Add phased prompts/checks (research, risk, editorial, reviewer) in one runtime
- [FAILING] **S4) Pre-delivery gate hardening** - Enforce deterministic fail/abstain gates for citation/paywall/diversity/budget
- [FAILING] **S4a) Abstain render closure** - Brief-level abstain must suppress normal issue cards, placeholders, and full citation dumps
- [FAILING] **S4b) Per-issue evidence binding** - Retrieval, issue planning, validation, persistence, and rendering must share issue-specific allowlists
- [IN_PROGRESS] **S5) Operational report templates** - Standardize issue-centered daily brief, event-risk brief, and portfolio-delta outputs
- [FAILING] **S5a) Delivered-claim derivations** - `What Changed` and visible citations must derive only from surviving delivered claims
- [FAILING] **S5b) Thesis language safety** - Bottom-line generation must reject malformed token-stitched prose
- [FAILING] **S6) Reliability metrics** - Track citation failure, retry, abstain, budget-per-report, and latency-to-delivery
- [IN_PROGRESS] **S7) Model-layer redesign** - Introduce provider-agnostic issue planner and claim composer contracts


