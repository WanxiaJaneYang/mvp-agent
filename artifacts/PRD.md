# Product Requirements Document (PRD) — Financial News & Macro Literature Review Assistant (MVP / v1)

## 1. Purpose
Build a local-first application that automatically collects financial news and macro/policy commentary, then produces reliable, citation-grounded daily analysis and major-event alerts to help retail investors make better strategic decisions.

The product is designed to reduce the need for users to actively track markets, while still keeping them informed when meaningful changes occur.

## 2. Target Users
**Primary users**
- Normal retail investors (non-finance professionals).
- Primarily long-term ETF holders investing spare funds.

**Secondary users (future)**
- Users with more complex portfolios (stocks + ETFs + multi-asset) who want portfolio-aware relevance and risk flags.

## 3. Scope
### In-scope (v1 / MVP)
- **Daily brief**: once per day, generate a literature-review-style synthesis of macro + market narratives.
- **Major event alerts**: notify users when significant events occur (e.g., major policy events, major macro releases, major market moves, major narrative shifts).
- **Cite everything**: all claims in AI-generated content must include evidence citations.
- **Local-first**: runs locally on the user’s machine.
- **Lightweight UI**:
  - A simple daily analysis page (local web page).
  - Email delivery for daily brief and alerts.
- **Portfolio input (manual)**:
  - Simple UI form to input holdings (tickers + weights).
  - Portfolio relevance scoring is included as “risk flags” (no explicit trade actions).

### Out of scope (v1)
- Brokerage integrations (e.g., Webull), OAuth linking, account syncing.
- High-frequency/real-time trading signals.
- Explicit buy/sell instructions.
- Paid subscriptions, cloud deployment, multi-tenant hosting (planned later).
- Full compliance framework (not-for-profit open-source positioning), beyond basic guardrails and disclaimers.

## 4. Key Use Cases & User Stories
### Daily brief
1. As a user, I want a daily summary of important macro/policy and market narratives so I don’t need to continuously read news.
2. As a user, I want the summary to show:
   - prevailing view,
   - counterarguments,
   - minority view,
   - and “what would falsify / what to watch” indicators,
   so I understand uncertainty and can make my own decisions.
3. As a user, I want every claim to be backed by citations so I can verify information quickly.

### Major event alerts
4. As a user, I want immediate alerts for major events so I can respond if needed.
5. As a user, I want alerts to be rate-limited and concise to avoid stress and information overload.

### Portfolio-aware relevance (manual input)
6. As a user, I want the system to flag which narratives are relevant to my portfolio exposures, so I can focus attention efficiently.
7. As a user, I want risk flags and scenario impacts, not direct investment instructions.

## 5. Product Principles
1. **Reliability first**: no uncited claims; prefer abstaining over hallucinating.
2. **Evidence-led outputs**: citations at the claim/bullet level (v1 minimum).
3. **User autonomy**: present risks and opportunities; user decides.
4. **Low anxiety UX**: concise, rate-limited alerts; daily digest as default.
5. **Local-first, cloud-ready**: architecture should support migration to cloud later.

## 6. Functional Requirements

### 6.1 Source ingestion
- Support source types:
  - RSS/Atom feeds (XML) → hydrate to HTML articles.
  - HTML pages (direct).
  - PDFs (e.g., reports, statements).
  - Optional: JSON APIs for market/macro time series (v1 can start minimal).
- Maintain a **Source Registry** (config file) defining:
  - source URL(s), type, fetch interval, tags (macro/policy/markets), credibility tier, and parsing strategy.
- Paywall handling:
  - If full text cannot be extracted reliably or appears paywalled, store metadata + snippet + link out.
- Deduplication:
  - canonical URL + hash for exact duplicates;
  - near-duplicate detection is optional in v1 (recommended).

### 6.2 Normalization & enrichment
- Clean text extraction from HTML/PDF into standardized document records.
- Store document metadata:
  - source, publisher, URL, published time, fetched time, title.
- Tagging (v1 baseline):
  - topics (macro, inflation, rates, growth, equity risk, credit, FX, commodities, etc.)
  - entities/tickers (best-effort)
  - doc_type classification (news / policy statement / minutes / speech / report / commentary)

### 6.3 Indexing & retrieval (grounded generation support)
- Hybrid retrieval:
  - keyword search (FTS/BM25)
  - semantic search (vector embeddings)
- Retrieval must support:
  - recency weighting
  - credibility weighting
  - diversity constraint (avoid one-publisher dominance)

### 6.4 Literature-review synthesis (core)
- Output format must include:
  - **Prevailing view**
  - **Counterarguments**
  - **Minority view**
  - **What to watch / falsification indicators**
  - **Citations per bullet/claim**
- “Cite everything” enforcement:
  - System must validate that each output bullet has at least one citation referencing ingested evidence.
  - If citations are missing/invalid, system must retry or remove the claim.

### 6.5 Daily brief delivery
- Generate a daily brief once per day (user timezone).
- Deliver via:
  - Email (preferred)
  - Local “Daily Brief” page (HTML)
- Include:
  - a “what changed since yesterday” section (v1: lightweight heuristic acceptable)

### 6.6 Major event alerts
- Trigger alerts based on a scoring framework (defined in spec later), considering:
  - event importance,
  - confidence/evidence,
  - relevance (global + portfolio relevance if available),
  - and rate limiting.
- Alert format:
  - short summary (3–6 bullets),
  - why it matters,
  - what to watch next,
  - citations.

### 6.7 Portfolio input & relevance
- UI allows manual input:
  - tickers + weights (required)
  - optional: region/currency/risk preference (optional)
- System maps narratives to exposures (v1: basic mapping):
  - direct ticker match,
  - sector/region inference where available,
  - factor tags optional (deferred).

## 7. Non-Functional Requirements

### 7.1 Reliability & faithfulness
- No uncited factual claims.
- System must be able to show evidence references (URLs + timestamps) for every bullet.
- Must handle insufficient evidence by abstaining or marking uncertainty.

### 7.2 Performance
- Local-first performance target:
  - daily pipeline completes within a reasonable time on consumer hardware (exact SLA not required for v1).
- Incremental ingestion recommended to avoid reprocessing everything daily.

### 7.3 Privacy & security
- Portfolio data stored locally.
- No cloud storage required for v1.
- API keys (if used) stored locally in environment variables or config file.

### 7.4 Maintainability
- Source registry is config-driven.
- Components are modular: ingestion, extraction, indexing, synthesis, delivery.

## 8. Content & UX Requirements
- Tone: calm, concise, evidence-based.
- No sensational phrasing.
- Provide balanced views (prevailing/counter/minority).
- Include explicit “what could prove this wrong” indicators.

## 9. Success Criteria (MVP)
1. Daily brief generated and delivered successfully every day.
2. All bullets include valid citations (no uncited claims).
3. Users can search and open cited sources from the report.
4. Major alerts trigger for clearly major events with low noise (rate limiting prevents spam).
5. Users can input holdings and see relevance/risk flags tied to their portfolio.

## 10. Acceptance Criteria (Testable)
### Citation enforcement
- Every bullet in “Prevailing / Counter / Minority / Watchlist” has ≥1 citation.
- Citations reference actual ingested documents/chunks and include URL + published timestamp.
- If evidence is insufficient, the system outputs “insufficient evidence” rather than inventing.

### Paywall policy
- For paywalled/blocked sources, the system stores:
  - title, publisher, published time, link, snippet (if available),
  - and does not fabricate full text.

### Daily brief
- Produces stable structured output sections.
- Includes at least one primary/official source when topic is policy-related (if available in sources).

### Alerts
- Enforces a maximum alerts/day limit per user.
- Alerts are short and cite evidence.

### Portfolio
- Users can input and update holdings.
- System produces relevance tags / risk flags tied to holdings.

## 11. Risks & Mitigations
- **Hallucinations / uncited claims**
  - Mitigation: strict evidence-pack generation + validator/retry loop + abstain policy.
- **Paywalls / crawling restrictions**
  - Mitigation: metadata/snippet + link-out policy; prefer RSS/official sources.
- **Alert noise**
  - Mitigation: scoring thresholds + rate limiting + bundling into daily brief.
- **Source quality drift**
  - Mitigation: credibility tiers and later a reviewed allowlist/blocklist.

## 12. Open Questions / TBD (to finalize during design)
1. Daily brief template (sections, max length).
2. Major alert triggers definition + thresholds.
3. Initial source list and credibility tiering strategy.
4. RAG tuning specifics (chunk size, overlap, retrieval weights, diversity constraints).
5. Quality evaluation plan (gold query set, regression tests).
6. ETF look-through and factor exposure modeling approach (v2).

## 13. Phased Delivery Plan
### Phase 1: MVP core (local)
- Source registry + ingestion + extraction
- Indexing (keyword + vector)
- Daily brief synthesis with strict citations
- Daily page + email delivery
- Basic major event alert triggers + rate limiting
- Manual portfolio input + basic relevance scoring

### Phase 2: Refinement (post-MVP)
- Narrative shift detection improvements
- More robust source scoring and dynamic source proposals with validation gate
- Better portfolio exposure mapping (sector/region/factor, ETF look-through)
- Improved evaluation suite and monitoring

### Phase 3: Cloud/subscription (future)
- Multi-user auth + hosting + billing
- Push notifications
- Shared global corpus + user-specific personalization layer
