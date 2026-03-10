# Status Matrix

This is the canonical modelled/coded/verified status view for the repository's major delivery areas.

Definitions:
- `modelled`: the area is described in the modelling artifacts or backlog.
- `coded`: the area has committed runtime or support code in the repository.
- `verified`: the coded area has committed tests or validators covering it in the current tree.

| Area | Modelled | Coded | Verified | Evidence |
|------|----------|-------|----------|----------|
| Source registry and active source subset | yes | yes | yes | `artifacts/modelling/source_registry.yaml`, `artifacts/runtime/v1_active_sources.yaml`, `apps/agent/runtime/source_scope.py`, `tests/agent/runtime/test_source_scope.py` |
| Orchestrator and pipeline stage framework | yes | yes | yes | `artifacts/modelling/pipeline.md`, `apps/agent/orchestrator.py`, `apps/agent/pipeline/types.py`, `tests/agent/test_orchestrator.py` |
| Ingestion, extraction, normalization, and dedup | yes | yes | yes | `artifacts/modelling/pipeline.md`, `apps/agent/ingest/`, `tests/agent/ingest/` |
| Retrieval and evidence-pack assembly | yes | yes | yes | `artifacts/modelling/pipeline.md`, `apps/agent/retrieval/`, `tests/agent/retrieval/` |
| Citation validation and abstain shaping | yes | yes | yes | `artifacts/modelling/citation_contract.md`, `apps/agent/validators/citation_validator.py`, `apps/agent/synthesis/postprocess.py`, `tests/agent/validators/test_citation_validator.py`, `tests/agent/synthesis/test_postprocess.py` |
| Budget guard and budget ledger | yes | yes | yes | `artifacts/PRD.md`, `artifacts/PROJECT_FACT.md`, `apps/agent/runtime/budget_guard.py`, `apps/agent/runtime/cost_ledger.py`, `tests/agent/runtime/test_budget_guard.py`, `tests/agent/runtime/test_cost_ledger.py` |
| Daily-brief runtime and local HTML output | yes | yes | yes | `artifacts/PRD.md`, `apps/agent/daily_brief/runner.py`, `apps/agent/daily_brief/synthesis.py`, `apps/agent/delivery/html_report.py`, `tests/agent/daily_brief/test_runner.py`, `tests/agent/daily_brief/test_synthesis.py`, `tests/agent/delivery/test_html_report.py` |
| Alert scoring and policy gates | yes | no | no | `artifacts/modelling/alert_scoring.md`, `artifacts/modelling/backlog.json` (`M006`) |
| Alert delivery runtime | yes | no | no | `artifacts/PRD.md`, `artifacts/modelling/backlog.json` (`M010`) |
| Eval harness and golden cases | yes | yes | yes | `evals/run_eval_suite.py`, `evals/golden/`, `tests/evals/test_run_eval_suite.py` |
| Portfolio relevance mapping | yes | no | no | `artifacts/PRD.md`, `artifacts/modelling/backlog.json` (`M009`) |

Priority note:
- The working daily-brief path is ahead of alert delivery. Alert delivery remains modelled but is intentionally downstream of the daily-brief path in `artifacts/modelling/backlog.json`.
