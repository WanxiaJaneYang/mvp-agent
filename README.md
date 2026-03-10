# MVP Agent

Local-first financial news and macro literature-review assistant.

This repository contains the modelling artifacts and early runtime components for an assistant that:
- ingests financial/macro sources (RSS, HTML, PDF),
- produces citation-grounded daily briefs and major-event alerts,
- enforces strict budget and safety guardrails.

## Current Phase

This project is currently in the modelling + early implementation phase.

Completed modelling artifacts:
- `artifacts/modelling/source_registry.yaml`
- `artifacts/modelling/data_model.md`
- `artifacts/modelling/pipeline.md`
- `artifacts/modelling/citation_contract.md`
- `artifacts/modelling/alert_scoring.md`
- `artifacts/modelling/backlog.json`

Current runtime validation narrows the full catalogue to an active source subset first:
- `artifacts/runtime/v1_active_sources.yaml`
- initial US-first active source subset:
  - `fed_press_releases`
  - `us_bls_news`
  - `us_bea_news`
  - `reuters_business`
  - `wsj_markets`

## Core Non-Negotiables

1. No uncited factual claims in generated analysis.
2. Respect paywall policies (`metadata_only` means no fabricated full text).
3. Enforce hard budget caps and stop on limit violations.
4. Keep the system local-first for data and portfolio context.

See:
- `artifacts/PRD.md`
- `artifacts/PROJECT_FACT.md`
- `AGENTS.md`

## Repository Layout

```text
apps/
  agent/
    runtime/              # Early runtime modules (e.g., budget guard)
artifacts/
  PRD.md                  # Product requirements
  PROJECT_FACT.md         # Hard constraints
  modelling/              # Modelling pack and planning docs
tests/
  agent/runtime/          # Unit tests
docs/plans/               # Planning notes
```

## Quick Start

Use Python 3.11+ (3.14 also works for current test scope).

Install the supported local toolchain:

```bash
python -m pip install -e ".[dev]"
```

Lint and type-check commands are available through the toolchain, but they are informational today:
- not CI-gated yet
- currently fail on pre-existing repo-wide issues that are outside this tooling slice

Run lint:

```bash
python -m ruff check apps tests scripts
```

Run type checks:

```bash
python -m mypy apps
```

Run tests:

```bash
python -m unittest discover -s tests -t . -p "test_*.py" -v
```

Run repository validation:

```bash
python scripts/validate_artifacts.py
python scripts/validate_decision_record_schema.py
python -m compileall -q apps tests scripts
```

## Working Conventions

- Use small, isolated branches and separate MRs for independent tasks.
- Follow `explore -> plan -> code -> verify -> commit`.
- Update progress tracking in `claude-progress.txt` for significant work.
- Follow MR policy in `.codex/mr-flow-and-approvals.md`.

## Notes

- This project is not a trading signal engine and should not produce buy/sell instructions.
- Outputs are intended to provide evidence-grounded scenarios and risk flags.
