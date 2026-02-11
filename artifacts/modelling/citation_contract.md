# Citation Contract — Evidence Grounding Rules

**Purpose:** Define how every claim in synthesis outputs must be backed by citations to stored evidence.

**Scope:** Applies to all AI-generated content: daily briefs, major event alerts, synthesis summaries.

---

## 1. Citation Object Format

Every citation references a stored document/chunk with the following structure:

```json
{
  "id": "cite_<uuid>",
  "source_id": "fed_press_releases",
  "doc_id": "doc_<uuid>",
  "chunk_id": "chunk_<uuid>",
  "url": "https://www.federalreserve.gov/newsevents/pressreleases/...",
  "title": "Federal Reserve announces...",
  "published_at": "2026-02-10T14:00:00Z",
  "fetched_at": "2026-02-11T02:15:00Z",
  "quote_span": {
    "start": 150,
    "end": 320,
    "text": "...actual quoted text snippet..."
  }
}
```

**Required fields:**
- `id`: Unique citation identifier
- `source_id`: Reference to source_registry.yaml entry
- `doc_id`: Document identifier in local store
- `chunk_id`: Chunk identifier (if chunked retrieval used)
- `url`: Canonical URL of source document
- `title`: Document title
- `published_at`: Original publication timestamp (ISO 8601)
- `fetched_at`: When we fetched/stored it (ISO 8601)

**Optional fields:**
- `quote_span`: Precise location + text excerpt from document (recommended for verification)

**Paywall-sourced citations:**
- If `source_registry.yaml` marks source as `paywall_policy: metadata_only`:
  - Citation MUST NOT include full-text quote_span
  - Citation includes: title, url, published_at, snippet (if available from RSS/meta)
  - System must NOT fabricate or extract paywalled full text

---

## 2. Bullet-Level Citation Rule

**Absolute requirement:** Every claim bullet in synthesis output must cite ≥1 stored evidence chunk.

**Applies to sections:**
- **Prevailing view** (mainstream narrative)
- **Counterarguments** (alternative perspectives)
- **Minority view** (dissenting/contrarian opinions)
- **What to watch** (falsification indicators, watchlist)

**Citation format in output:**
```markdown
- The Federal Reserve held rates steady at 5.25-5.50% citing persistent inflation concerns. [1][2]
```

Where `[1]`, `[2]` are citation IDs that map to full citation objects stored with the output.

**Inline citation placement:**
- Place citations immediately after the claim they support
- Multiple citations per bullet are encouraged (corroboration)
- Each citation must reference actual retrieved evidence

---

## 3. Validator Behavior

**Pre-output validation (mandatory):**

Before delivering any synthesis output, the system MUST run a citation validator that:

1. **Extracts all claim bullets** from Prevailing/Counter/Minority/Watch sections
2. **Checks each bullet** has ≥1 citation ID
3. **Verifies each citation ID** resolves to:
   - A valid doc_id/chunk_id in the local evidence store
   - A URL that matches the source_registry.yaml entry
   - A published_at timestamp (not missing/null)

**On validation failure:**

| Failure Type | Action |
|--------------|--------|
| Bullet has 0 citations | **Remove bullet** OR replace with `[Insufficient evidence to support this claim]` |
| Citation ID not found in store | **Remove citation** from bullet; if bullet has no remaining citations, apply above rule |
| Citation missing required fields (url, published_at) | **Remove citation**; if bullet has no remaining citations, apply above rule |
| Paywalled source cited with full-text quote | **Strip quote_span**, keep metadata-only citation |

**No exceptions:** If a claim cannot be cited, it must not appear in the output.

**Validator output:**
- Validation report JSON: `{ "total_bullets": N, "cited_bullets": M, "removed_bullets": K, "validation_passed": true/false }`
- If `validation_passed: false`, synthesis must be retried or flagged for review

---

## 4. Evidence-Pack Definition

**Purpose:** Define how retrieval builds a bounded, diverse set of evidence chunks for synthesis.

### 4.1 Retrieval Constraints

- **Max chunks per query:** 20–40 chunks (configurable, default 30)
- **Chunk size:** 300–800 tokens (configurable, default 500 tokens with 100-token overlap)
- **Recency window:** Prioritize last 7 days; include older if highly relevant (up to 30 days for context)

### 4.2 Diversity Constraints

To avoid one-source dominance (per PROJECT_FACTS.md):

1. **Publisher diversity:**
   - No single publisher (e.g., Reuters) can dominate >40% of evidence pack
   - If retrieval returns >40% from one publisher, down-sample and retrieve more from others

2. **Credibility tier diversity:**
   - Require ≥50% of evidence from Tier 1 or Tier 2 sources
   - Tier 4 (monitor-only) sources cannot exceed 15% of evidence pack

3. **Perspective diversity:**
   - For balanced synthesis, evidence pack should include:
     - Official/policy sources (Tier 1)
     - Mainstream news/analysis (Tier 2)
     - Alternative/contrarian views (Tier 3/4, if available)

### 4.3 Credibility Weighting

Retrieval scoring formula includes credibility tier:

```
retrieval_score = semantic_similarity * 0.5
                  + recency_score * 0.3
                  + credibility_score * 0.2
```

**Credibility score mapping:**
- Tier 1: 1.0
- Tier 2: 0.8
- Tier 3: 0.6
- Tier 4: 0.3

This ensures official/primary sources are weighted higher in retrieval, but still allows minority views.

### 4.4 Evidence-Pack Metadata

Each evidence pack generated for a synthesis run must store:

```json
{
  "pack_id": "pack_<uuid>",
  "query": "What is the Fed's current stance on rates?",
  "generated_at": "2026-02-11T08:00:00Z",
  "chunks": [
    { "chunk_id": "chunk_<uuid>", "source_id": "fed_press_releases", "score": 0.92, "credibility_tier": 1 },
    { "chunk_id": "chunk_<uuid>", "source_id": "wsj_markets", "score": 0.87, "credibility_tier": 2 },
    ...
  ],
  "diversity_stats": {
    "unique_publishers": 8,
    "tier_1_pct": 45,
    "tier_2_pct": 40,
    "tier_3_pct": 10,
    "tier_4_pct": 5,
    "max_publisher_pct": 35
  }
}
```

---

## 5. Paywall Rule

**Policy (from PROJECT_FACTS.md & source_registry.yaml):**

Sources marked `paywall_policy: metadata_only` in source_registry.yaml:
- Store: title, URL, published timestamp, RSS snippet (if available)
- Do NOT store or fabricate full-text content
- Do NOT extract content behind login/paywall

**Citation behavior:**

When citing a paywalled source:

✓ **Allowed:**
```markdown
- Markets fell sharply on inflation data. [Financial Times, "Stocks tumble as CPI exceeds forecasts", Feb 10, 2026]
```

Citation object includes:
```json
{
  "id": "cite_123",
  "source_id": "ft_markets",
  "url": "https://www.ft.com/content/...",
  "title": "Stocks tumble as CPI exceeds forecasts",
  "published_at": "2026-02-10T10:30:00Z",
  "fetched_at": "2026-02-11T02:00:00Z",
  "quote_span": null  // No full-text available
}
```

✗ **Not allowed:**
- Fabricating full-text quotes from paywalled articles
- Claiming to have read full content when only metadata is available
- Bypassing paywalls via scraping/archive services

**User experience:**
- Paywalled citations link out to source URL
- User can verify claim by visiting source (if they have subscription)
- System is transparent: "Source is paywalled; citation based on headline/snippet"

---

## 6. Explicit Abstain Language & Uncertainty Markers

**When to abstain:**

If retrieval yields insufficient evidence to support a claim, the system MUST abstain rather than guess.

**Abstain scenarios:**
1. No relevant chunks retrieved for a query
2. Only 1 low-credibility (Tier 4) source available
3. Evidence is contradictory and no clear consensus
4. Evidence is outdated (>30 days old for time-sensitive topics)

**Abstain language (use explicitly):**

Instead of unsupported claims, use:

- `[Insufficient evidence to assess this claim]`
- `[Data not yet available as of <date>]`
- `[Conflicting reports; unable to confirm]`
- `[No official statement found in available sources]`

**Uncertainty markers (when evidence is weak but present):**

- "According to limited available reports, ..." [cite Tier 3/4 sources]
- "Some sources suggest ... [cite], but official confirmation is pending."
- "Early indications from [source] show ... [cite], though this has not been widely reported."

**Confidence levels (optional future enhancement):**

Mark bullets with confidence scores based on:
- Number of corroborating sources
- Credibility tier of sources
- Recency of evidence

Example:
- `[HIGH CONFIDENCE] The Fed held rates at 5.25-5.50%. [1][2][3]` (3 Tier-1 sources)
- `[MEDIUM CONFIDENCE] Markets expect a rate cut in Q3. [4][5]` (2 Tier-2 sources)
- `[LOW CONFIDENCE] Some analysts predict recession. [6]` (1 Tier-4 source)

---

## 7. Citation Presentation in Outputs

### 7.1 Inline Citations

**Format:**
```markdown
## Prevailing View
- The Federal Reserve held rates steady at 5.25-5.50%, citing persistent inflation. [1][2]
- Q4 GDP grew 2.9%, slightly above expectations. [3]

## Counterarguments
- Some economists argue the Fed is over-tightening. [4][5]

## Minority View
- A few contrarian voices predict deflation by Q3. [6]

## What to Watch
- Next CPI release on March 12. [7]
- FOMC meeting minutes due March 20. [8]
```

### 7.2 Citation Reference Section

At the end of each synthesis output, include a **References** section:

```markdown
## References

[1] Federal Reserve. "FOMC Statement - February 2026". Published Feb 10, 2026. https://www.federalreserve.gov/...

[2] Reuters. "Fed holds rates steady, signals cautious approach". Published Feb 10, 2026. https://www.reuters.com/...

[3] U.S. Bureau of Economic Analysis. "GDP Fourth Quarter 2025 (Advance Estimate)". Published Jan 30, 2026. https://www.bea.gov/...

[4] Financial Times. "Is the Fed over-tightening? Economists debate". Published Feb 9, 2026. https://www.ft.com/... [Paywall]

[5] Brookings Institution. "Monetary Policy in an Uncertain Economy". Published Feb 8, 2026. https://www.brookings.edu/...

[6] Zero Hedge. "Deflation warnings ignored by mainstream". Published Feb 11, 2026. https://www.zerohedge.com/... [Monitor-only source]

[7] U.S. Bureau of Labor Statistics. "CPI Release Schedule". https://www.bls.gov/schedule/

[8] Federal Reserve. "FOMC Calendar". https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
```

**Reference format:**
- `[N] Publisher. "Title". Published <date>. <URL>`
- Add `[Paywall]` tag for paywalled sources
- Add `[Monitor-only source]` tag for Tier-4 sources
- Sort by citation number

---

## 8. Storage Schema (Reference)

**Citation table (SQLite):**

```sql
CREATE TABLE citations (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,  -- FK to sources table
    doc_id TEXT NOT NULL,     -- FK to documents table
    chunk_id TEXT,            -- FK to chunks table (nullable if doc-level)
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    published_at TEXT NOT NULL,  -- ISO 8601 timestamp
    fetched_at TEXT NOT NULL,    -- ISO 8601 timestamp
    quote_span_start INTEGER,    -- Character offset start (nullable)
    quote_span_end INTEGER,      -- Character offset end (nullable)
    quote_text TEXT,             -- Extracted quote (nullable, null for paywalled)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(id),
    FOREIGN KEY (doc_id) REFERENCES documents(id),
    FOREIGN KEY (chunk_id) REFERENCES chunks(id)
);

CREATE INDEX idx_citations_source ON citations(source_id);
CREATE INDEX idx_citations_doc ON citations(doc_id);
CREATE INDEX idx_citations_published ON citations(published_at);
```

**Synthesis-citations junction table:**

```sql
CREATE TABLE synthesis_citations (
    synthesis_id TEXT NOT NULL,  -- FK to synthesis_runs table
    citation_id TEXT NOT NULL,   -- FK to citations table
    section TEXT NOT NULL,       -- 'prevailing', 'counter', 'minority', 'watch'
    bullet_index INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (synthesis_id, citation_id, section, bullet_index),
    FOREIGN KEY (synthesis_id) REFERENCES synthesis_runs(id),
    FOREIGN KEY (citation_id) REFERENCES citations(id)
);
```

---

## 9. Implementation Checklist

Before marking this deliverable as complete, ensure:

- [ ] Citation object schema implemented in data_model.md
- [ ] Bullet-level citation rule enforced in synthesis prompts
- [ ] Citation validator implemented and tested
- [ ] Evidence-pack retrieval respects diversity + credibility constraints
- [ ] Paywall sources handled correctly (metadata-only, no full-text)
- [ ] Abstain language included in synthesis templates
- [ ] Citation presentation format implemented in output renderer
- [ ] Validator runs before every synthesis output delivery
- [ ] Test cases include: missing citations, paywalled sources, insufficient evidence scenarios

---

## 10. Example: Valid vs Invalid Outputs

### ✓ Valid Output (passes validation)

```markdown
## Prevailing View
- The Federal Reserve held rates at 5.25-5.50% in February, citing persistent inflation. [1][2]
- Q4 GDP grew 2.9%, slightly above consensus. [3]

## Counterarguments
- Some economists warn the Fed risks over-tightening into a slowdown. [4][5]

## Minority View
- [Insufficient evidence to represent minority views on this topic]

## What to Watch
- Next CPI release on March 12. [6]

## References
[1] Federal Reserve. "FOMC Statement". Feb 10, 2026. https://...
[2] Reuters. "Fed holds rates steady". Feb 10, 2026. https://...
[3] BEA. "GDP Q4 2025 Advance Estimate". Jan 30, 2026. https://...
[4] Financial Times. "Is the Fed over-tightening?". Feb 9, 2026. https://... [Paywall]
[5] Brookings. "Monetary Policy Debate". Feb 8, 2026. https://...
[6] BLS. "Economic Release Schedule". https://...
```

### ✗ Invalid Output (fails validation)

```markdown
## Prevailing View
- The Federal Reserve held rates at 5.25-5.50% in February.
  ❌ No citation

- Markets are expecting a rate cut in Q3.
  ❌ No citation (speculative claim)

## Counterarguments
- Some economists think inflation is actually falling faster than the Fed realizes. [99]
  ❌ Citation [99] does not exist in evidence store

## Minority View
- According to insider sources, the Fed will cut rates in March.
  ❌ No citation; "insider sources" is not a stored document

## References
[99] Anonymous. "Insider Fed leak". <no URL>
  ❌ Invalid citation: no URL, no published_at, not in source_registry
```

**Validator action:** Reject output, strip uncited bullets, retry synthesis with explicit "cite everything" instruction.

---

## 11. Summary

This citation contract ensures:

1. **No uncited claims** — Every bullet has ≥1 citation to stored evidence
2. **Validator enforcement** — Pre-delivery checks reject outputs with missing/invalid citations
3. **Evidence diversity** — Retrieval avoids one-source dominance, balances credibility tiers
4. **Paywall compliance** — Metadata-only for paywalled sources; no fabrication
5. **Explicit abstention** — "Insufficient evidence" over unsupported claims
6. **Transparency** — Citations include URL, timestamp, publisher; user can verify

**Next step:** Implement citation validator in `apps/agent/validators/citation_validator.py` and integrate into synthesis pipeline (see `pipeline.md`).
