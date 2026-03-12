# PRD v1.2 - Financial News & Macro Literature Review Assistant

**Version:** v1.2  
**Status:** Draft ready for redesign implementation  
**User timezone:** Asia/Singapore

## 1. Purpose
Build a local-first application that automatically collects financial news, macro/policy releases, and institutional commentary, then produces citation-grounded daily analysis and rate-limited major-event alerts for retail investors.

The product goal is not to summarize sources one by one. It should identify the most important issues of the day, synthesize competing arguments around each issue, and show exactly which evidence supports each argument.

## 2. Target Users
**Primary**
- Retail investors (non-finance professionals)
- Primarily long-term ETF holders investing spare funds

**Secondary (future)**
- Users with more complex portfolios (stocks + ETFs + multi-asset) who want portfolio-aware relevance and risk flags

## 3. Product Principles
1. **Reliability first:** no uncited factual claims; abstain if evidence is insufficient.
2. **Evidence-led outputs:** citations are attached at the claim level, not only at the page level.
3. **Argument-first synthesis:** outputs should look like short literature reviews, not source-by-source paraphrase.
4. **User autonomy:** scenarios and risks, not trade instructions.
5. **Low-anxiety UX:** concise digest by default; alerts are rare and bundled.
6. **Local-first, cloud-ready:** evidence handling stays deterministic and local; model providers are pluggable.

## 4. Scope

### 4.1 In-scope (v1 / MVP)
- **Daily brief:** once per day, issue-centered literature-review synthesis of macro + market narratives.
- **Major event alerts:** notify on significant events with rate limiting.
- **Cite everything:** every delivered claim must have valid evidence coverage.
- **Local-first evidence layer:** runs on the user's machine; portfolio data stored locally.
- **Model-assisted synthesis:** provider-agnostic interface with two first-class runtime paths:
  - OpenAI API via project-scoped API key
  - Codex OAuth via local `codex login` / ChatGPT sign-in
- **Lightweight UI:**
  - local daily analysis page (static HTML)
  - email delivery for daily brief and alerts
- **Portfolio input (manual):**
  - tickers + weights
  - relevance scoring as "risk flags" (no explicit buy/sell actions)

### 4.2 Out of scope (v1)
- Brokerage integrations / OAuth account linking / syncing
- Real-time trading signals and high-frequency alerts
- Explicit buy/sell instructions
- Paid subscriptions, multi-tenant hosting
- Full compliance framework beyond basic guardrails and disclaimers

## 5. MVP Defaults (Hard Numbers)

### 5.1 Daily brief
- **Schedule:** 07:05 Asia/Singapore daily
- **Important issues per brief:** target 2; allow 3 only when evidence diversity and information gain support a third distinct issue
- **Issue budget rule:** never force 3 issues; if the corpus only supports 1-2 distinct issues, the brief must stay at 1-2
- **Source-scarcity rule:** if the corpus cannot support 2 distinct issues with adequate diversity, render a compressed brief with 1 main issue + 2-3 key takeaways + a short watchlist instead of padding with thin issues
- **Per issue structure:**
  - issue title or question
  - short synthesis summary
  - prevailing argument
  - counter argument
  - minority argument when evidence exists
  - what to watch / falsification indicators
- **Max evidence items shown per argument:** 3
- **Max length:** about 1,200 words total (or equivalent token cap)
- **Citation rule:** every delivered claim includes valid citation coverage.

### 5.2 Alerts
- **Max alerts/day:** 3
- **Cooldown:** 60 minutes between alerts
- **Max length:** about 400 words
- **Format:** focused issue summary + why it matters + what to watch next
- **Citation rule:** every delivered claim includes valid citation coverage.

### 5.3 Ingestion & retrieval caps
- **Max new documents/day:** 200
- **Default per-source cap:** 10 docs/day (exceptions allowed for wires/SEC feeds)
- **Evidence pack:** max 30 chunks per synthesis/alert run
- **Publisher dominance cap:** <=40% from any single publisher
- **Tier mix requirement:** >=50% Tier 1/2; Tier 4 <=15%
- **Recency bias:** prioritize last 7 days; include up to 30 days for context

### 5.4 Budget guard (runtime)
- **Monthly:** $100
- **Daily:** $3
- **Hourly:** $0.10
- On exceed: **hard stop** (no automatic retries)

## 6. Functional Requirements

### 6.1 Source ingestion
Supported source types:
- RSS/Atom (preferred)
- HTML pages
- PDFs (reports, statements)

Maintain a config-driven **Source Registry** defining:
- source URL(s), type, fetch interval, tags, credibility tier, parsing strategy, paywall policy

Paywall handling:
- if paywalled or blocked: store metadata + snippet + link; do not fabricate text

Deduplication:
- canonical URL + content hash (exact duplicates)
- near-duplicate detection: optional in v1

Fair access / rate limiting:
- respect source terms
- implement global and per-source request limits
- for SEC EDGAR: moderate automated requests per SEC guidance

### 6.2 Normalization & enrichment
- Extract clean text from HTML/PDF into a standardized document record.
- Store metadata: source, publisher, URL, title, published time, fetched time, paywall policy.
- Baseline tagging:
  - topics (macro, inflation, rates, growth, equity risk, credit, FX, commodities, tech, etc.)
  - entities/tickers (best effort)
  - doc type (news / policy statement / minutes / speech / report / commentary)

### 6.3 Indexing & retrieval
- Hybrid retrieval target:
  - keyword search (SQLite FTS5)
  - semantic search (vector embeddings) for non-paywalled chunks
- Retrieval supports:
  - recency weighting
  - credibility weighting
  - diversity constraint (avoid one-publisher dominance)
- The evidence layer must remain deterministic and auditable even when semantic retrieval is added later.

### 6.4 Daily brief generation architecture
The daily brief must follow this pipeline:

1. **Deterministic evidence layer**
   - ingestion / normalize / dedup / chunk / retrieval / citation store / budget guard
2. **Issue planner (model layer)**
   - consumes bounded evidence pack and optional prior-brief context
   - outputs structured `IssueMap[]`
3. **Claim composer (model layer)**
   - consumes `IssueMap[]` plus citations
   - outputs structured `ClaimObject[]`
4. **Validator / critic**
   - deterministic citation and evidence checks are mandatory
   - optional critic pass can reject shallow source-by-source paraphrase
5. **Renderer**
   - HTML/email consume structured issue and claim objects

This replaces the earlier single-query, section-bullet synthesis design.

### 6.5 Required daily brief output shape
Each daily brief should read like a short literature review across 2-3 issues when evidence supports that count.

Issue-budget and scarcity rules:
- default to 2 issues when the corpus supports multiple distinct debates
- allow 3 issues only when the third issue adds clear incremental information and does not materially overlap the first 2
- if source scarcity, low diversity, or high overlap prevents 2 distinct issues, render a compressed brief with:
  - `bottom_line` / brief thesis
  - `top_takeaways`
  - 1 main issue block
  - `watchlist`
- issues that fail distinctness or information-gain thresholds must be merged, demoted to takeaways/watchlist, or dropped rather than forced into the body

For each issue, the system must produce:
- `issue_question`
- `summary`
- `prevailing` claim
- `counter` claim
- `minority` claim when evidence exists
- `watch` claim
- visible evidence items tied to each argument
- `why_it_matters`
- `novelty_vs_prior_brief`

Each argument under one issue must discuss the same underlying thesis or question.

### 6.6 Model-layer structured contracts
The issue planner must output JSON objects similar to:
- `issue_id`
- `issue_question`
- `thesis_hint`
- `supporting_evidence_ids`
- `opposing_evidence_ids`
- `minority_evidence_ids`
- `watch_evidence_ids`

The claim composer must output JSON objects similar to:
- `claim_id`
- `issue_id`
- `claim_kind` (`prevailing`, `counter`, `minority`, `watch`)
- `claim_text`
- `supporting_citation_ids`
- `opposing_citation_ids`
- `confidence`
- `novelty_vs_prior_brief`
- `why_it_matters`

Free-form prose generation without structured JSON is out of scope for the model interface.

### 6.7 Provider Runtime Modes
The model layer must stay provider-agnostic above the transport/runtime boundary.

Supported runtime modes:
- `deterministic`
  - no model calls; legacy local fallback for fixtures and abstain-safe paths
- `openai`
  - uses OpenAI API credentials and quota via the Responses API
- `codex-oauth`
  - uses the locally authenticated Codex CLI runtime backed by ChatGPT sign-in
  - must not require `OPENAI_API_KEY`

Provider invariants:
- issue planner and claim composer still consume the same internal typed inputs
- issue planner and claim composer still return the same schema-valid JSON
- renderer, validator, and decision record layers must not care which provider runtime produced the JSON
- provider switching must not weaken citation, paywall, or budget constraints

### 6.8 Daily brief delivery
- Generate once per day in user timezone.
- Deliver via:
  - email
  - local "Daily Brief" HTML page
- Show exact evidence supporting each argument.
- Show what changed since the prior brief through claim-level delta, not a renderer-only heuristic.

### 6.9 Major event alerts
Trigger categories (v1):
- **Policy (Tier 1):** new central bank statement/minutes/speech/press release
- **Macro releases (Tier 1):** CPI/jobs/GDP and other major official releases
- **Corporate material events (Tier 1 via SEC 8-K / major IR):** material filings/events; focus on index-relevant large caps or user watchlist
- **Narrative shift (Tier 2+):** heuristic based on topic distribution shift and contradiction rate vs trailing 7 days

Alert scoring combines:
- importance + evidence strength + confidence + relevance - noise risk

Rate limiting:
- enforce cooldown + daily cap
- bundle minor items into next daily brief

### 6.10 Portfolio input & relevance
UI allows manual input:
- tickers + weights (required)

Relevance mapping (v1):
- direct ticker match
- curated sector/theme tags mapping table shipped as defaults

Outputs:
- relevance tags and "risk flags" (no trade actions)

## 7. Non-Functional Requirements

### 7.1 Reliability & faithfulness
- No uncited factual claims.
- Every delivered claim references stored evidence with URL + published timestamp.
- Handle insufficient evidence by abstaining explicitly.
- Model layers must never bypass deterministic evidence and citation validation.

### 7.2 Performance
- Daily pipeline completes on consumer hardware (no strict SLA in v1).
- Incremental ingestion to avoid reprocessing everything daily.

### 7.3 Privacy & security
- Portfolio stored locally.
- API keys stored locally in environment variables / `.env` (never committed).
- Codex OAuth credentials remain under the user's local Codex auth store and must not be copied into repo artifacts.

### 7.4 Maintainability
- Source registry is config-driven.
- Modular components: ingestion, extraction, indexing, evidence, issue planning, claim composition, validation, delivery.
- Provider integrations must be replaceable without changing renderer or validation contracts.
- CLI-backed providers must be bounded, deterministic at the transport layer, and safe to disable when auth is missing.

## 8. Content & UX Requirements
- Calm, concise, evidence-based tone.
- Issue-centered structure rather than one global narrative bucket.
- Balanced views within each issue (prevailing / counter / minority).
- Explicit "what could prove this wrong" indicators.
- Clear paywall transparency (headline/snippet only).
- Visible evidence under each argument, not hidden only in a references list.

## 9. Success Criteria (MVP)
1. Daily brief generated and delivered successfully every day.
2. Daily brief consistently surfaces 2-3 important issues when evidence supports them.
3. Delivered claims include valid citations and pass validator checks.
4. Users can open cited sources from the report.
5. Major alerts trigger for clearly major events with low noise (rate limited).
6. Users can input holdings and see portfolio relevance / risk flags.

## 10. Acceptance Criteria (Testable)

### Citation enforcement
- Every delivered claim has valid citation coverage.
- Citations resolve to ingested docs/chunks and include URL + published timestamp.
- If evidence is insufficient: output "insufficient evidence" rather than inventing.

### Issue planning
- Daily brief generation does not depend on a single top-term query alone.
- The system produces 2-3 issue candidates when evidence diversity supports it.
- `prevailing`, `counter`, and `minority` claims for an issue all address the same issue question.

### Claim composition
- Claims are synthesized from multiple evidence items when available.
- `why_it_matters` and `novelty_vs_prior_brief` are stored as structured fields.
- Output is schema-valid JSON before rendering.

### Paywall policy
- Paywalled sources store metadata/snippet only.
- No fabricated full-text quotes from paywalled content.

### Daily brief
- Stable structured output.
- Includes Tier 1 sources when topic is policy-related (if available).
- Renderer displays issue summaries plus evidence-backed arguments.

### Alerts
- Max alerts/day enforced.
- Cooldown enforced.
- Alerts are concise and cite evidence.

### Portfolio
- Users can input and update holdings.
- Relevance tags / risk flags tied to holdings.

## 11. Risks & Mitigations
- **Hallucinations / uncited claims:** strict evidence packs + validator + abstain policy.
- **Shallow synthesis:** issue planner + claim composer + critic pass to reject source-by-source paraphrase.
- **Weak retrieval pack:** bounded evidence pack plus future semantic retrieval improvements.
- **Paywalls / crawling restrictions:** metadata/snippet + link-out; prefer RSS and official sources.
- **Alert noise:** thresholds + rate limiting + bundling.
- **Source quality drift:** credibility tiers and allowlist/blocklist.
- **Provider/runtime drift:** keep a shared JSON contract above provider adapters and validate provider outputs before rendering.

## 12. Phased Delivery Plan

### Phase 1: MVP core (local)
- Source registry + ingestion + extraction
- Indexing (FTS5 + embeddings target, deterministic fallback allowed)
- Issue planner + claim composer contracts
- Daily brief renderer driven by structured issues and claims
- Daily page + email delivery
- Major event triggers + rate limiting
- Manual portfolio input + basic relevance scoring

### Phase 2: Refinement
- Narrative shift detection improvements
- More robust source scoring and automatic source proposals with validation gate
- Better portfolio exposure mapping (sector/region/factor; ETF look-through)
- Improved evaluation suite + monitoring
- Stronger critic pass and historical-delta quality checks

### Phase 3: Cloud/subscription (future)
- Multi-user auth + hosting + billing
- Push notifications
- Shared global corpus + user personalization layer

## 13. References for Implementation Notes (non-requirements)
- Agent harness patterns for long-running, budget-bounded workflows: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- SQLite FTS5 full-text search: https://www.sqlite.org/fts5.html
- SEC EDGAR fair access guidance (rate limits / moderation): https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data

## 14. In-Scope Strengthening Backlog (2026-03-12)
These improvements are within this PRD's local-first, citation-grounded, and non-advisory scope.

1. Decision record per run
- Persist issue maps, claim objects, citations used, rejected alternatives, risk flags, budget usage, and final rationale.

2. Retrieval memory from validated historical outputs
- Embed/index only approved historical syntheses and retrieve similar prior cases before claim composition.

3. Internal role-lane orchestration in one runtime
- Add explicit phases: evidence, planner, composer, critic, validator.

4. Stronger pre-delivery quality gates
- Hard-fail or abstain on citation coverage, paywall policy, source-diversity, and budget violations.

5. Operational templates
- Add fixed templates for daily brief, event-risk brief, and portfolio-delta review with issue-level checks.

6. Feedback-loop metrics
- Track citation failure rate, retry rate, abstain rate, budget per successful report, issue count per brief, and time to delivery.
