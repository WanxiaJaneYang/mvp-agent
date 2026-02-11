# PROJECT_FACTS.md — Non-Negotiables & Operating Constraints

## Project
Financial News & Macro Literature Review Assistant (MVP/v1).
Local-first system that ingests sources (RSS/HTML/PDF) and produces:
- daily literature-review style macro/market synthesis
- major event alerts
- portfolio-aware relevance flags (manual holdings input)
All outputs must be evidence-grounded with citations.

## Phase
We are in **MODELLING PHASE**:
- Turn PRD into an executable modelling pack: source registry, data model, pipeline, citation contract, alert scoring, backlog JSON, eval plan.
- No UI polishing or production deployment work yet.

## User & Environment
- Primary user: retail long-term ETF holder
- Timezone: Asia/Singapore
- Runs locally first; cloud optional later.

## Budget & Safety Caps (hard limits)
- Monthly budget cap: USD 100
- Daily cap: USD 3.00
- Hourly cap: USD 0.10
- Never run uncontrolled loops.
- Every run must enforce:
  - max_output_tokens per call (default 800–1200)
  - max tool calls per run
  - max pages fetched per run
  - stop immediately when daily/hourly budget is reached.

## Reliability Rules (hard requirements)
1) **No uncited factual claims.**
2) Every bullet/claim must include ≥1 citation to stored evidence:
   - URL + published timestamp (when available)
   - internal doc/chunk ID in our store
3) If evidence is insufficient: output “insufficient evidence” and do not guess.
4) Avoid one-source dominance: diversify publishers and prefer official/primary sources for policy items.

## Content Policy / UX Tone
- Calm, concise, non-sensational.
- Balanced structure:
  - Prevailing view
  - Counterarguments
  - Minority view
  - What to watch / falsification indicators
- No investment instructions (“buy/sell”); present scenarios and uncertainty.

## Local Data & Privacy
- Portfolio data stored locally only.
- API keys are secrets: use `.env` and never commit them.

## Modelling Outputs (Definition of Done)
The modelling pack must exist and be consistent with PRD:
- `artifacts/modelling/source_registry.yaml`
- `artifacts/modelling/data_model.md` (SQLite + FTS plan)
- `artifacts/modelling/pipeline.md`
- `artifacts/modelling/citation_contract.md`
- `artifacts/modelling/alert_scoring.md`
- `artifacts/modelling/backlog.json` (valid JSON + acceptance criteria)
- `evals/` includes at least 10 golden cases + citation validation checks

## Preferred Model Provider (current)
- Anthropic Claude via Messages API (tool-using agent).
- Keep prompts + artifacts provider-agnostic so we can swap models later.
