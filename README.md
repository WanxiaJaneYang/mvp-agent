# MVP Agent

Local-first financial news and macro literature-review assistant.

This repository contains the modelling artifacts and early runtime components for an assistant that:
- ingests financial/macro sources (RSS, HTML, PDF),
- indexes evidence in local SQLite/FTS5 with hybrid lexical plus semantic retrieval scoring,
- produces citation-grounded daily briefs,
- delivers daily briefs to local HTML plus optional email on a user-timezone schedule,
- implements alert scoring, policy gates, and local alert delivery runtime,
- enforces strict budget and safety guardrails.

## Current Phase

This project is currently in early implementation with the modelling pack still serving as the planning source of truth.

Implemented in-tree today:
- daily-brief runtime, scheduled HTML/email delivery, and citation/postprocess guardrails
- persistent SQLite/FTS5 retrieval with lexical plus semantic scoring
- alert scoring, policy-gate helpers, and alert delivery runtime
- eval harness with 12 golden cases
- manual portfolio relevance mapping with local runtime persistence

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

Historical open-issue execution order for the now-landed daily-brief program:
- the sequence `#135 -> #128 -> #129 -> #130 -> #131 -> #138 -> #134 -> #132 -> #133 -> #136 -> #69 -> #137 -> #74` landed on `master` through PRs `#143`-`#157`
- treat `issue_139.md` and `docs/plans/2026-03-13-daily-brief-integrity-issue-mapping.md` as historical reference material for that completed execution stream
- re-triage new work from current repo status, `docs/status-matrix.md`, `artifacts/modelling/backlog.json`, and fresh GitHub issue state instead of resuming the old list

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
    alerts/               # Alert scoring and policy gates
    daily_brief/          # Daily-brief runtime stages
    delivery/             # HTML, email, and schedule helpers
    portfolio/            # Manual holdings input and relevance mapping
    runtime/              # Runtime modules (e.g., budget guard)
evals/
  golden/                # Golden cases for current runtime contracts
artifacts/
  PRD.md                  # Product requirements
  PROJECT_FACT.md         # Hard constraints
  modelling/              # Modelling pack and planning docs
tests/
  agent/                  # Runtime and tooling unit tests
  evals/                  # Eval harness tests
docs/plans/               # Planning notes
```

## Quick Start

Use Python 3.11+ (3.14 also works for current test scope).

Install the supported local toolchain:

```bash
python -m pip install -e ".[dev]"
```

Lint and type-check commands are required and CI-gated:
- pull requests to `master` must pass both commands
- use the same local commands before pushing changes

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

Run the active-subset daily brief against live feeds:

```bash
python scripts/run_daily_brief.py
```

The live runner now defaults to `--provider auto`, which resolves providers in this order:
- `codex-oauth`
- `openai`

If neither provider is available, the live command fails closed instead of silently falling back to the deterministic path.

Run the deterministic fixture-backed daily brief slice:

```bash
python scripts/run_daily_brief_fixture.py
```

The fixture runner now applies the same local critic gate as the live runner by default.
If a caller bypasses the critic when using `run_fixture_daily_brief(...)` directly, the publish summary records `analytical_status=not_run` instead of treating the brief as passed.

Run the fixture slice with real OpenAI issue planning and claim composition:

```bash
set OPENAI_API_KEY=...
python scripts/run_daily_brief_fixture.py --provider openai --openai-model gpt-4o-mini
```

Run the fixture slice with subscription-backed Codex OAuth synthesis:

```bash
codex login status
python scripts/run_daily_brief_fixture.py --provider codex-oauth
```

Provider-backed demo modes:
- `openai`
  - uses `OPENAI_API_KEY` and OpenAI API billing/quota
- `codex-oauth`
  - uses the local `codex login` session
  - does not require `OPENAI_API_KEY`
  - can return `ok` or a validator-driven `abstained` result depending on model output quality

Provider-backed fixture demos now use the same critic-driven hold/publish gate as the live runner.

The current provider-agnostic seam is covered in `tests/agent/daily_brief/test_runner.py` for both `run_fixture_daily_brief(...)` and `run_daily_brief(...)`.

Run the fixture slice with the modeled Asia/Singapore schedule and email delivery:

```bash
python scripts/run_daily_brief_fixture.py --smtp-host smtp.example.test --sender-email briefs@example.test --recipient-email pm@example.test
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
- Alert policy/runtime work stays downstream of daily-brief stabilization in the open-issue program order, even though local alert delivery runtime support already exists in-tree.
- Portfolio relevance remains a local-first risk-flag surface, not buy/sell guidance.
- The live daily-brief slice starts with the current RSS-backed active subset and skips sources that are temporarily blocked or unavailable.
- Daily-brief scheduling defaults to `07:05 Asia/Singapore`, with timezone overrides available from the runner scripts.
