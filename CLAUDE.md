# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## Project Overview
**Financial News & Macro Literature Review Assistant (MVP/v1)**  
Local-first Python app that ingests macro/market sources (RSS/HTML/PDF) and produces **citation-grounded** daily briefs + major-event alerts for retail investors.

**Current Phase:** Modelling (designing system architecture, schemas, and pipelines before implementation)

---

## Non‑Negotiables
1. **No uncited factual claims.** Every bullet/claim must have ≥1 valid citation (URL + published timestamp).
2. **Local-first.** No cloud storage requirements for v1.
3. **Paywall compliance.** If a source is `paywall_policy: metadata_only`, do **not** fabricate full text.
4. **Budget safety.** Respect strict caps and stop when caps are reached (see Budget section).
5. **Minimize context bloat.** Read only files needed for the current step.

---

## Cost & Context Discipline (Claude Code)
Claude Code costs scale with context size; long sessions can degrade as context fills. Use the built-in commands intentionally.

### Session Hygiene
- Use `/cost` to inspect session token spend (API-billed usage); if you’re on a subscription, use `/stats` instead.
- Use `/clear` between unrelated tasks to avoid stale context being repeatedly processed.
- Use `/compact` only when needed; keep compaction instructions specific to the current objective.

### Default Output Limits
- Keep responses concise: **≤ 120 lines** unless explicitly requested.
- Prefer checklists + diffs over long explanations.
- Never paste full articles; store IDs/snippets only.

---

## Setup & Environment (Windows)

### Activate venv
```cmd
.venv\Scripts\activate
```

### Install deps (once code exists)
```cmd
pip install -r requirements.txt
```

---

## Repository Structure (authoritative)

```
artifacts/
├── PRD.md                      # Authoritative requirements (frozen)
├── PROJECT_FACT.md             # Constraints (budget, timezone, policies)
└── modelling/
    ├── source_registry.yaml
    ├── data_model.md
    ├── pipeline.md
    ├── citation_contract.md
    ├── alert_scoring.md
    └── backlog.json

apps/agent/                      # Future: agent runner, tools, RAG store, validators
evals/                           # Future: regression checks for modelling outputs
ops/                             # Future: operational scripts and utilities
claude-progress.txt              # Durable progress log (append-only)
```

---

## Development Workflow (small, verifiable steps)
Follow: **Explore → Plan → Execute → Verify → Log**

1) **Explore**
- Read only the artifact(s) needed for this step.

2) **Plan**
- State exactly which files will change (ideally 1–4).
- Define a clear verification step (command/assertion/checklist).

3) **Execute**
- Make the smallest change that satisfies the step.

4) **Verify**
- Run the verification command(s) and report results.
- If verification fails, fix the root cause (don’t suppress).

5) **Log**
- Append to `claude-progress.txt`:
  - what changed
  - files touched
  - verification run + outcome
  - the next single step

---

## Architecture Principles

### Daily Pipeline (planned)
```
fetch → extract → normalize → chunk → index → retrieve → synthesize → validate citations → deliver
```

### Output Structure Requirements
All synthesis outputs must include:
- **Prevailing view** (mainstream narrative)
- **Counterarguments** (alternative perspectives)
- **Minority view** (dissenting opinions)
- **What to watch** (falsification indicators)
- **Citations per bullet** (mandatory, validated)

---

## Modelling Deliverables (Definition of Done)

A. `artifacts/modelling/source_registry.yaml` ✅  
B. `artifacts/modelling/data_model.md` (SQLite schema + FTS plan + IDs + indices)  
C. `artifacts/modelling/pipeline.md` (stages + failure handling + incremental runs)  
D. `artifacts/modelling/citation_contract.md` ✅  
E. `artifacts/modelling/alert_scoring.md` (thresholds + rate limits + bundling)  
F. `artifacts/modelling/backlog.json` (tickets w/ acceptance criteria; valid JSON)

---

## RAG & Retrieval Guidance

### Context Management
- Never paste long articles; store locally and reference by ID.
- Retrieve selectively (top relevant chunks only).
- Diversify sources (avoid single-publisher dominance).
- Prefer credible sources (Tier 1/2 for policy/macro).
- Cite stored evidence, not “memory”.

### Retrieval Strategy (planned)
- Hybrid: keyword (FTS/BM25) + semantic (vector embeddings)
- Recency weighting for time-sensitive content
- Credibility tier weighting
- Diversity constraints

---

## Tooling Requirements
All tools must be:
- Narrowly scoped (no overlapping responsibilities)
- Clearly named (purpose obvious)
- Token-efficient (return IDs + short snippets + metadata)
- Robust (timeouts, missing pages, paywalls)

---

## Budget & Safety (two layers)

### Layer 1: Claude Code interaction discipline
- Keep tasks small + verifiable.
- Avoid multi-agent “teams” unless necessary.
- Check `/cost` periodically (API users) and `/clear` between tasks.

### Layer 2: App runtime budget guard (local config)
- Budget caps live in `.env` (local-only; never committed) and are enforced by the app/harness **before** any model call.
- Guard should hard-fail when cap exceeded to prevent runaway loops.

Recommended `.env` keys:
- `BUDGET_MONTHLY_USD=100`
- `BUDGET_DAILY_USD=3`
- `BUDGET_HOURLY_USD=0.50`
- `BUDGET_MODE=hard_fail`
- `BUDGET_STATE_PATH=.budget_state.json`

### Safety Rules
- Never run uncontrolled loops.
- Enforce max tool calls per run.
- Enforce max pages fetched per run.
- Stop immediately when budget caps are reached.

---

## Content Policy
- Calm, concise, evidence-based
- No sensational phrasing
- Balanced presentation of views
- Explicit uncertainty markers
- No investment instructions (scenarios + risks only)
- Portfolio: relevance/risk flags only (no buy/sell signals)

---

## Key Constraints
- **User timezone:** Asia/Singapore
- **Target user:** Retail long-term ETF holders
- **Provider:** Anthropic Claude (Claude Code now; Messages API later)
- **Storage:** SQLite (local)
- **Secrets:** `.env` (gitignored)

---

## Phase Completion Criteria
Modelling phase is complete when:
- [ ] All deliverables (A–F) exist and validate
- [ ] `backlog.json` validates with acceptance criteria
- [ ] Citation validator passes
- [ ] Budget guard implemented and enabled by default
- [ ] At least 10 golden test cases in `evals/`
