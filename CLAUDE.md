# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Financial News & Macro Literature Review Assistant (MVP/v1).
Local-first Python application that ingests macro/market sources (RSS/HTML/PDF) and produces citation-grounded daily briefs + major-event alerts for retail investors.

**Current Phase:** Modelling (designing system architecture, schemas, and pipelines before implementation)

## Setup & Environment

### Initial Setup (Windows)
```cmd
# Activate virtual environment
.venv\Scripts\activate

# Install dependencies (once artifacts exist)
pip install -r requirements.txt
```

### Running the Agent
```cmd
# Run modelling phase
python -m apps.agent.main run_modelling --idea "..."
```

## Repository Structure

```
artifacts/
├── PRD.md                    # Authoritative requirements (frozen)
├── PROJECT_FACT.md           # Constraints (budget, timezone, policies)
├── modelling/                # Stable modelling outputs
│   ├── source_registry.yaml  # Source definitions with credibility tiers
│   ├── data_model.md         # SQLite schema + FTS indexing plan
│   ├── pipeline.md           # Daily pipeline stages
│   ├── citation_contract.md  # Citation validation rules
│   ├── alert_scoring.md      # Alert thresholds & rate limits
│   └── backlog.json          # Build tickets with acceptance criteria
└── runs/<timestamp>/         # Per-run generated outputs + logs

apps/agent/                   # Agent runner, tools, RAG store, validators
evals/                        # Regression checks for modelling outputs
ops/                          # Operational scripts and utilities
claude-progress.txt           # Durable progress log (append-only)
```

## Architecture Principles

### Absolute Rules (Non-Negotiable)
1. **No uncited factual claims** - Every claim requires ≥1 citation with URL + timestamp
2. **Local-first** - No cloud dependencies; all data stored locally
3. **Budget safety** - Hard caps enforced (daily: $3, hourly: $0.10, monthly: $100)
4. **Deterministic artifacts** - Every run writes to `artifacts/runs/<timestamp>/`
5. **Minimize context bloat** - Just-in-time retrieval; load only relevant snippets/IDs

### Daily Pipeline (Planned)
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

## Development Workflow

### Modelling Phase Loop
1. **Explore** - Retrieve minimal evidence and PRD constraints
2. **Plan** - Outline file changes and rationale
3. **Execute** - Write/update artifacts
4. **Verify** - Run validators (JSON schema + citation checks)
5. **Update** `claude-progress.txt` with changes and test results

### Progress Tracking
Always update `claude-progress.txt` each session with:
- What you changed
- What files were created/modified
- What remains to be done
- What validators were run and their results

## Modelling Deliverables (Definition of Done)

The following files must exist and be consistent with PRD:

A. `artifacts/modelling/source_registry.yaml`
   - RSS/HTML/PDF sources with tags, credibility tiers, fetch cadence, paywall policy

B. `artifacts/modelling/data_model.md`
   - SQLite schema (sources/documents/chunks/citations/portfolio/alerts/runs)
   - FTS (Full-Text Search) indexing plan
   - Chunking strategy

C. `artifacts/modelling/pipeline.md`
   - Daily pipeline stages with error handling
   - Incremental vs full refresh logic

D. `artifacts/modelling/citation_contract.md`
   - Valid citation format (chunk/doc ID + URL + timestamp)
   - Abstain behavior when evidence is insufficient
   - Citation validation rules

E. `artifacts/modelling/alert_scoring.md`
   - v1 thresholds for major events
   - Rate limiting policy (max alerts/day)
   - Alert bundling strategy

F. `artifacts/modelling/backlog.json`
   - Build tickets with acceptance criteria
   - Must validate against schema

## RAG & Retrieval Guidance

### Context Management
- **Never paste long articles** - Store locally and reference by ID
- **Retrieve selectively** - Top relevant chunks only
- **Diversify sources** - Avoid single-publisher dominance
- **Prefer credible sources** - Official/primary sources for policy content
- **Include citations** - Reference stored evidence, not "memory"

### Retrieval Strategy (Planned)
- Hybrid: keyword (FTS/BM25) + semantic (vector embeddings)
- Recency weighting for time-sensitive content
- Credibility tier weighting
- Diversity constraints

## Tooling Requirements

All tools must be:
- **Narrowly scoped** (no overlap between tools)
- **Clearly named** (purpose obvious from name)
- **Token-efficient** (return IDs, short snippets, metadata only)
- **Robust** (handle timeouts, missing pages, paywalls gracefully)

## Budget & Safety

### Hard Limits (config.json)
- Monthly: $100
- Daily: $3.00
- Hourly: $0.10
- Per-call: max_output_tokens default 800-1200

### Safety Rules
- Never run uncontrolled loops
- Stop immediately when budget caps are reached
- Enforce max tool calls per run
- Enforce max pages fetched per run

## Content Policy

### Tone & Style
- Calm, concise, evidence-based
- No sensational phrasing
- Balanced presentation of views
- Explicit uncertainty markers

### Output Requirements
- Every bullet includes citations
- "Insufficient evidence" over hallucination
- No investment instructions (present scenarios, not advice)
- Portfolio risk flags only (no buy/sell signals)

## Validation & Testing

### Citation Validator
- Every bullet has ≥1 valid citation
- Citations reference actual ingested docs/chunks
- URLs + timestamps included
- Invalid citations trigger retry or removal

### Modelling Validation
Run before considering phase complete:
- JSON schema validation for backlog.json
- Citation contract compliance check
- All required deliverables (A-F) exist
- Budget guards implemented

## Key Constraints

- **User timezone:** Asia/Singapore
- **Target user:** Retail long-term ETF holders
- **Model provider:** Anthropic Claude (via Messages API with tools)
- **Storage:** SQLite (local)
- **Secrets:** Use `.env` file (never commit)
- **Platform:** Windows (local-first, cloud-ready architecture)

## Phase Completion Criteria

Modelling phase is complete when:
- [ ] All deliverables (A-F) exist and validate
- [ ] `backlog.json` validates with acceptance criteria
- [ ] Citation validator passes
- [ ] Budget guard implemented and enabled by default
- [ ] At least 10 golden test cases in `evals/`
