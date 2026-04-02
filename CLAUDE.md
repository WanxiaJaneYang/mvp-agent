# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## Project Overview
**Financial News & Macro Literature Review Assistant (MVP/v1)**  
Local-first Python app that ingests macro and market sources (RSS, HTML, PDF), stores evidence locally, and produces citation-grounded daily briefs plus major-event alerts.

**Current Phase:** Early implementation. The modelling pack still matters, but the repository already contains runtime code, delivery paths, storage, validators, and eval coverage.

---

## Non-Negotiables
1. **No uncited factual claims.** Every bullet or claim must have at least one valid citation with URL and published timestamp.
2. **Local-first.** No cloud storage requirements for v1.
3. **Paywall compliance.** If a source is `paywall_policy: metadata_only`, do not fabricate full text.
4. **Budget safety.** Respect strict caps and stop when caps are reached.
5. **Minimize context bloat.** Read only files needed for the current step.

---

## Cost & Context Discipline
- Keep responses concise unless the user explicitly asks for depth.
- Prefer diffs, checklists, and file-level summaries over long narration.
- Never paste full articles; store IDs, snippets, and metadata instead.
- Use `/clear` between unrelated tasks and `/compact` only when the session actually needs it.

---

## Setup & Environment

Install the local dev toolchain with:

```bash
python -m pip install -e ".[dev]"
```

Core verification commands:

```bash
python scripts/validate_artifacts.py
python scripts/validate_decision_record_schema.py
python -m ruff check apps tests scripts tools
python -m mypy apps tools
python -m unittest discover -s tests -t . -p "test_*.py" -v
```

Daily-brief runtime and eval entry points:

```bash
python scripts/run_daily_brief.py
python scripts/run_daily_brief_fixture.py
python -m unittest discover -s tests/evals -p "test_*.py" -v
```

---

## Repository Reality

```text
apps/
  agent/
    alerts/        # alert scoring and policy gates
    daily_brief/   # daily-brief runtime
    delivery/      # html, email, and scheduler helpers
    ingest/        # fetch/extract/normalize/dedup helpers
    pipeline/      # shared run/stage types and pipeline helpers
    portfolio/     # portfolio input and relevance helpers
    retrieval/     # chunking and retrieval helpers
    runtime/       # budget and runtime helpers
    storage/       # sqlite runtime persistence
    synthesis/     # synthesis post-processing
    validators/    # citation and output validators
tests/
  agent/           # runtime and tooling tests
  evals/           # eval harness tests
scripts/           # validation and runner entry points
artifacts/
  modelling/       # modelling contracts, schemas, and backlog
docs/
  plans/           # planning and implementation notes
```

Before assuming an area is still only planned, check:
- `README.md`
- `docs/status-matrix.md`
- the relevant `apps/agent/` and `tests/agent/` packages

---

## Workflow

Follow the repo and Trellis flow:

```text
explore -> plan -> execute -> verify -> record
```

Before editing:
- read `AGENTS.md`
- read `.trellis/workflow.md`
- read `README.md` and `docs/status-matrix.md` when the task touches repo-level workflow or structure
- read only the code and artifacts needed for the task

When recording work:
- prefer Trellis task and workspace recording
- treat `claude-progress.txt` as legacy context, not the primary workflow contract

---

## Current Implementation Reality

Implemented in-tree today includes:
- daily-brief runtime plus local HTML and email delivery
- ingestion, retrieval, SQLite persistence, and citation validation
- alert scoring, policy gates, and alert delivery runtime
- eval harness coverage and golden cases
- portfolio relevance mapping and local persistence

The modelling artifacts still matter, but they are no longer the whole repo.

---

## Architecture Principles

### Daily Pipeline
```text
fetch -> extract -> normalize -> chunk -> index -> retrieve -> synthesize -> validate citations -> deliver
```

### Output Requirements
All synthesis outputs must include:
- prevailing view
- counterarguments
- minority view
- what to watch
- citations per bullet

---

## Retrieval Guidance

### Context Management
- Never paste long articles; store locally and reference by ID.
- Retrieve selectively from the indexed corpus.
- Diversify sources; avoid single-publisher dominance.
- Prefer higher-credibility sources for policy and macro claims.
- Cite stored evidence, not memory.

### Retrieval Strategy
- Hybrid lexical plus semantic retrieval is already part of the runtime direction.
- Recency, source quality, and diversity should stay explicit in reasoning and validation.

---

## Tooling Expectations
All tools should be:
- narrowly scoped
- clearly named
- token-efficient
- robust against timeouts, missing pages, and paywalls

---

## Budget & Safety

### Interaction discipline
- Keep tasks small and verifiable.
- Avoid multi-agent teams unless they are actually necessary.
- Check cost and context hygiene before long or repetitive loops.

### Runtime guardrails
- Budget caps live in `.env` and must never be bypassed casually.
- The runtime should fail closed on hard budget limits.
- Stop on configured hard limits instead of trying to push through.

Recommended `.env` keys:
- `BUDGET_MONTHLY_USD=100`
- `BUDGET_DAILY_USD=3`
- `BUDGET_HOURLY_USD=0.10`
- `BUDGET_MODE=hard_fail`
- `BUDGET_STATE_PATH=.budget_state.json`

---

## Content Policy
- Calm, concise, evidence-based
- No sensational phrasing
- Balanced presentation of views
- Explicit uncertainty markers
- No direct investment instructions
- Portfolio handling should stay at relevance and risk framing, not buy or sell signals

---

## Key Constraints
- **Target user:** Retail long-term ETF holders
- **Storage:** SQLite (local)
- **Secrets:** `.env` (gitignored)
- **Runtime provider choice:** Check the current runner and config; do not assume a single provider stack
- **Timezone and user context:** Do not hardcode a static user timezone; use current task context, project facts, and runtime inputs instead
