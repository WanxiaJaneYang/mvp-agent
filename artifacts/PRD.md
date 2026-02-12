# PRD v1.1 — Financial News & Macro Literature Review Assistant (Local‑First)

**Version:** v1.1 (clarified spec)  
**Status:** Draft ready for modelling + implementation  
**User timezone:** Asia/Singapore

## 1. Purpose
Build a local‑first application that automatically collects financial news, macro/policy releases, and institutional commentary, then produces **citation‑grounded** daily analysis and **rate‑limited** major‑event alerts for retail investors.

The product reduces the need to actively track markets while keeping users informed when meaningful changes occur.

## 2. Target Users
**Primary**
- Retail investors (non‑finance professionals)
- Primarily long‑term ETF holders investing spare funds

**Secondary (future)**
- Users with more complex portfolios (stocks + ETFs + multi‑asset) who want portfolio‑aware relevance and risk flags

## 3. Product Principles
1. **Reliability first:** no uncited factual claims; abstain if evidence is insufficient.
2. **Evidence‑led outputs:** citations are attached at the bullet/claim level.
3. **User autonomy:** scenarios and risks, not trade instructions.
4. **Low‑anxiety UX:** concise digest by default; alerts are rare and bundled.
5. **Local‑first, cloud‑ready:** architecture can later migrate to cloud.

## 4. Scope

### 4.1 In‑scope (v1 / MVP)
- **Daily brief**: once per day, literature‑review‑style synthesis of macro + market narratives.
- **Major event alerts**: notify on significant events with rate limiting.
- **Cite everything**: every bullet must have ≥1 citation.
- **Local‑first**: runs on the user’s machine; portfolio data stored locally.
- **Lightweight UI**:
  - local daily analysis page (static HTML)
  - email delivery for daily brief and alerts
- **Portfolio input (manual)**:
  - tickers + weights
  - relevance scoring as “risk flags” (no explicit buy/sell actions)

### 4.2 Out of scope (v1)
- Brokerage integrations / OAuth account linking / syncing
- Real‑time trading signals and high‑frequency alerts
- Explicit buy/sell instructions
- Paid subscriptions, multi‑tenant hosting
- Full compliance framework beyond basic guardrails and disclaimers

## 5. MVP Defaults (Hard Numbers)

### 5.1 Daily brief
- **Schedule:** 07:05 Asia/Singapore daily
- **Sections (max bullets):**
  - Prevailing view: 3–6
  - Counterarguments: 2–5
  - Minority view: 1–4
  - What to watch / falsification indicators: 3–6
  - What changed since yesterday: ≤3
- **Max total bullets:** 24
- **Max length:** ~1,200 words (or equivalent token cap)
- **Citation rule:** every bullet includes ≥1 valid citation.

### 5.2 Alerts
- **Max alerts/day:** 3
- **Cooldown:** 60 minutes between alerts
- **Max length:** ~400 words
- **Format:** 3–6 bullets + “why it matters” + “what to watch next”
- **Citation rule:** every bullet includes ≥1 valid citation.

### 5.3 Ingestion & retrieval caps
- **Max new documents/day:** 200
- **Default per‑source cap:** 10 docs/day (exceptions allowed for wires/SEC feeds)
- **Evidence pack:** max 30 chunks per synthesis/alert query
- **Publisher dominance cap:** ≤40% from any single publisher
- **Tier mix requirement:** ≥50% Tier 1–2; Tier 4 ≤15%
- **Recency bias:** prioritize last 7 days; include up to 30 days for context.

### 5.4 Budget guard (runtime)
- **Monthly:** $100
- **Daily:** $3
- **Hourly:** $0.50
- On exceed: **hard stop** (no automatic retries).

## 6. Functional Requirements

### 6.1 Source ingestion
Supported source types:
- RSS/Atom (preferred)
- HTML pages
- PDFs (reports, statements)

Maintain a config‑driven **Source Registry** defining:
- source URL(s), type, fetch interval, tags, credibility tier, parsing strategy, paywall policy

Paywall handling:
- if paywalled/blocked: store metadata + snippet + link; **do not** fabricate text

Deduplication:
- canonical URL + content hash (exact duplicates)
- near‑duplicate detection: optional in v1 (recommended for later)

Fair access / rate limiting:
- respect source terms
- implement global and per‑source request limits
- for SEC EDGAR: moderate automated requests per SEC guidance

### 6.2 Normalization & enrichment
- Extract clean text from HTML/PDF into a standardized document record.
- Store metadata: source, publisher, URL, title, published time, fetched time, paywall policy.
- Baseline tagging:
  - topics (macro, inflation, rates, growth, equity risk, credit, FX, commodities, tech, etc.)
  - entities/tickers (best effort)
  - doc type (news / policy statement / minutes / speech / report / commentary)

### 6.3 Indexing & retrieval (for grounded generation)
- Hybrid retrieval:
  - keyword search (SQLite FTS5)
  - semantic search (vector embeddings) for non‑paywalled chunks
- Retrieval supports:
  - recency weighting
  - credibility weighting
  - diversity constraint (avoid one‑publisher dominance)

### 6.4 Literature‑review synthesis (core)
Required output sections:
- Prevailing view
- Counterarguments
- Minority view
- What to watch / falsification indicators
- References (expanded citations list)

Citation enforcement:
- system validates that each bullet has ≥1 citation
- on failure, remove bullet or replace with explicit abstain language

### 6.5 Daily brief delivery
- Generate once per day in user timezone.
- Deliver via:
  - email
  - local “Daily Brief” HTML page
- Include a “what changed since yesterday” section (heuristic acceptable in v1).

### 6.6 Major event alerts
Trigger categories (v1):
- **Policy (Tier‑1):** new central bank statement/minutes/speech/press release
- **Macro releases (Tier‑1):** CPI/jobs/GDP and other major official releases
- **Corporate material events (Tier‑1 via SEC 8‑K / major IR):** material filings/events; focus on index‑relevant large caps or user watchlist
- **Narrative shift (Tier‑2+):** heuristic based on topic distribution shift and/or contradiction rate vs trailing 7 days

Alert scoring combines:
- importance + evidence strength + confidence + relevance − noise risk

Rate limiting:
- enforce cooldown + daily cap
- bundle minor items into next daily brief

### 6.7 Portfolio input & relevance
UI allows manual input:
- tickers + weights (required)

Relevance mapping (v1):
- direct ticker match
- curated sector/theme tags mapping table shipped as defaults

Outputs:
- relevance tags and “risk flags” (no trade actions)

## 7. Non‑Functional Requirements

### 7.1 Reliability & faithfulness
- No uncited factual claims.
- Every bullet references stored evidence with URL + published timestamp.
- Handle insufficient evidence by abstaining explicitly.

### 7.2 Performance
- Daily pipeline completes on consumer hardware (no strict SLA in v1).
- Incremental ingestion to avoid reprocessing everything daily.

### 7.3 Privacy & security
- Portfolio stored locally.
- API keys stored locally in environment variables / `.env` (never committed).

### 7.4 Maintainability
- Source registry is config‑driven.
- Modular components: ingestion, extraction, indexing, synthesis, delivery.

## 8. Content & UX Requirements
- Calm, concise, evidence‑based tone.
- Balanced views (prevailing / counter / minority).
- Explicit “what could prove this wrong” indicators.
- Clear paywall transparency (headline/snippet only).

## 9. Success Criteria (MVP)
1. Daily brief generated and delivered successfully every day.
2. All bullets include valid citations (validator passes).
3. Users can open cited sources from the report.
4. Major alerts trigger for clearly major events with low noise (rate limited).
5. Users can input holdings and see portfolio relevance / risk flags.

## 10. Acceptance Criteria (Testable)

### Citation enforcement
- Every bullet has ≥1 citation.
- Citations resolve to ingested docs/chunks and include URL + published timestamp.
- If evidence is insufficient: output “insufficient evidence” rather than inventing.

### Paywall policy
- Paywalled sources store metadata/snippet only.
- No fabricated full‑text quotes from paywalled content.

### Daily brief
- Stable structured output.
- Includes Tier‑1 sources when topic is policy‑related (if available).

### Alerts
- Max alerts/day enforced.
- Cooldown enforced.
- Alerts are concise and cite evidence.

### Portfolio
- Users can input and update holdings.
- Relevance tags / risk flags tied to holdings.

## 11. Risks & Mitigations
- **Hallucinations / uncited claims:** strict evidence packs + validator + abstain policy.
- **Paywalls / crawling restrictions:** metadata/snippet + link‑out; prefer RSS and official sources.
- **Alert noise:** thresholds + rate limiting + bundling.
- **Source quality drift:** credibility tiers and allowlist/blocklist.

## 12. Phased Delivery Plan

### Phase 1: MVP core (local)
- Source registry + ingestion + extraction
- Indexing (FTS5 + embeddings)
- Daily brief synthesis with strict citations
- Daily page + email delivery
- Major event triggers + rate limiting
- Manual portfolio input + basic relevance scoring

### Phase 2: Refinement
- Narrative shift detection improvements
- More robust source scoring and automatic source proposals with validation gate
- Better portfolio exposure mapping (sector/region/factor; ETF look‑through)
- Improved evaluation suite + monitoring

### Phase 3: Cloud/subscription (future)
- Multi‑user auth + hosting + billing
- Push notifications
- Shared global corpus + user personalization layer

## 13. References for Implementation Notes (non‑requirements)
- Agent harness patterns for long‑running, budget‑bounded workflows: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents  
- Claude citations feature (optional, still validate locally): https://platform.claude.com/docs/en/build-with-claude/citations  
- SQLite FTS5 full‑text search: https://www.sqlite.org/fts5.html  
- SEC EDGAR fair access guidance (rate limits / moderation): https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
