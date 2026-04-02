# Issue Discovery V0 Issue Sequencing Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Define the recommended child-issue order under `#193` so Phase 1 implementation proves the new issue-discovery path before adding bounded enrichment, review gates, or primary-path cutover.

**Architecture:** The execution order follows the repo's two-speed redesign. First land additive schema, deterministic event visibility, single-event candidate generation, cheap scoring, shortlist selection, and shadow evaluation. Only after that proof path is stable should the work expand into bounded enrichment, review routing, hard gates, and the final primary-path switch.

**Tech Stack:** GitHub issues, Python pipeline/runtime code under `apps/agent/`, SQLite runtime storage, JSON artifact writers, local eval suite under `evals/`.

---

## Parent Issue

- Keep GitHub issue `#193` as the parent issue for `Issue Discovery v0 / Market Intelligence Redesign`.
- Do not create a second top-level epic.
- All child issues below should link back to `#193`.

## Recommended Execution Order

Primary sequence:

1. `[P0] Add Phase 1 additive schema and artifact contracts for issue discovery v0`
2. `[P1] Add OpenBB-backed market data adapter for supplemental market_stream inputs`
3. `[P0] Implement deterministic event clustering v0 for canonical news items`
4. `[P0] Implement single-event issue candidate builder v0`
5. `[P0] Implement discovery-score feature extraction for issue candidates`
6. `[P0] Build shortlist selector v0 using discovery score and existing issue_dedup gates`
7. `[P0] Add issue discovery shadow mode and dual-path comparison artifacts`
8. `[P0] Add selector evals and shadow rollout checks for daily brief`
9. `[P1] Implement bounded issue enricher v0 for shortlisted candidates`
10. `[P1] Implement enrichment-score and post-enrichment rerank/select`
11. `[P1] Split briefing review into integrity critic, value gate, and fixed revision routing`
12. `[P1] Add hard gates for claim-evidence binding, numeric checks, freshness, and source floors`
13. `[P1] Promote issue discovery v0 from shadow to primary for daily brief`

Execution notes:

- `#2` is intentionally second, but it remains supplemental and must not become the hard prerequisite for proving the news-first selector path.
- Issue 5 in the stream breakdown is intentionally optional and is not part of the blocking primary sequence.
- If resources are constrained, `#9` through `#12` can be delayed until `#8` proves the shortlist and shadow path.
- `#4` can be expanded into multi-event composition later, but it must not block the single-event path.

## Stream Breakdown

### Stream A: Make Events Visible

#### Issue 1

Title:
- `[P0] Add Phase 1 additive schema and artifact contracts for issue discovery v0`

Goal:
- add the Phase 1 tables and dual-written artifacts without changing the current authoritative path

Dependencies:
- none

Acceptance checks:
- schema migration runs cleanly
- baseline mode is unchanged
- dual-written artifacts persist successfully

Artifacts / outputs:
- additive runtime tables
- new JSON artifact writers

#### Issue 2

Title:
- `[P1] Add OpenBB-backed market data adapter for supplemental market_stream inputs`

Goal:
- add an optional OpenBB-backed adapter that supplies structured market data to `market_stream` as supplemental inputs

Dependencies:
- hard dependency: Issue 1
- sequencing recommendation: land before Issue 3, but keep it non-blocking to the rest of the proof path

Acceptance checks:
- configured OpenBB datasets can be fetched and normalized
- baseline mode remains unchanged when the feature flag is off
- supplemental artifacts are written deterministically
- adapter failures degrade cleanly without breaking `market_stream`

Artifacts / outputs:
- `openbb_market_inputs.json`
- `openbb_adapter_report.json`
- optional market snapshot augmentation fields

Rollout notes:
- feature-flagged only
- supplemental only
- do not make OpenBB authoritative for selector-quality evaluation before shadow thresholds exist

#### Issue 3

Title:
- `[P0] Implement deterministic event clustering v0 for canonical news items`

Goal:
- cluster `canonical_news_item` inputs per run and emit deterministic event artifacts

Dependencies:
- Issue 1
- Issue 2 is allowed to land first but must not be required for baseline clustering

Acceptance checks:
- same-run clustering is reproducible
- singleton count, cluster count, and average cluster size are reported
- no LLM clustering is introduced

Artifacts / outputs:
- `events.json`
- `event_items.json`
- `clustering_report.json`

### Stream B: Build Issue Candidates

#### Issue 4

Title:
- `[P0] Implement single-event issue candidate builder v0`

Goal:
- generate one base candidate per eligible event and make the event-to-candidate path traceable

Dependencies:
- Issue 3

Acceptance checks:
- `MAX_CANDIDATES_PER_EVENT = 1`
- every candidate is traceable to its source event
- candidate builder report is emitted

Artifacts / outputs:
- `issue_candidates.json`
- `candidate_builder_report.json`

#### Issue 5

Title:
- `[P1] Add limited multi-event candidate composition with relation_kind mapping`

Goal:
- support a narrow multi-event candidate path without allowing unconstrained many-to-many composition

Dependencies:
- Issue 4

Acceptance checks:
- exactly one `primary_driver` per multi-event candidate
- at most two auxiliary events per candidate
- `relation_kind` explains why events were combined

Artifacts / outputs:
- `issue_candidate_events.json`

### Stream C: Cheap Scoring And Shortlist

#### Issue 6

Title:
- `[P0] Implement discovery-score feature extraction for issue candidates`

Goal:
- land the feature inputs and reason codes for the cheap upstream score

Dependencies:
- Issue 4
- Issue 5 may land in parallel, but must not block the single-event path

Acceptance checks:
- every feature has explicit inputs and reason codes
- `pre_enrich_score` is produced deterministically
- no hidden bonus term exists

Artifacts / outputs:
- score breakdown fields in `issue_candidates.json`

#### Issue 7

Title:
- `[P0] Build shortlist selector v0 using discovery score and existing issue_dedup gates`

Goal:
- produce the top-K shortlist while reusing the existing overlap, information-gain, and issue-budget logic

Dependencies:
- Issue 6

Acceptance checks:
- `issue_dedup` is wrapped or moved into selector logic
- shortlist explainability is emitted
- the old path remains intact

Artifacts / outputs:
- `selection_contexts.json`
- `issue_selections.json`
- shortlist comparison artifacts

### Stream D: Shadow Mode And Proof

#### Issue 8

Title:
- `[P0] Add issue discovery shadow mode and dual-path comparison artifacts`

Goal:
- run the new selector beside the current baseline path without changing the authoritative brief output

Dependencies:
- Issue 7

Acceptance checks:
- `ISSUE_DISCOVERY_MODE=baseline|shadow|primary` works
- shadow mode does not affect the current authoritative brief path
- baseline and selector outputs are both inspectable

Artifacts / outputs:
- baseline-vs-selector comparison artifacts

#### Issue 9

Title:
- `[P0] Add selector evals and shadow rollout checks for daily brief`

Goal:
- add evaluation and rollout thresholds so the branch can prove the new selector before cutover

Dependencies:
- Issue 8

Acceptance checks:
- eval suite runs
- shadow rollout checklist exists
- thresholds for switching to `primary` are explicit

Artifacts / outputs:
- selector eval outputs
- rollout checklist

### Stream E: Bounded Enrichment

#### Issue 10

Title:
- `[P1] Implement bounded issue enricher v0 for shortlisted candidates`

Goal:
- add targeted retrieval and follow-up only for shortlisted issues

Dependencies:
- Issue 9

Acceptance checks:
- enrichment stays within explicit budgets
- only shortlisted issues enter enrichment
- `confidence_score` is not used in any selection total

Artifacts / outputs:
- `issue_enrichments.json`

#### Issue 11

Title:
- `[P1] Implement enrichment-score and post-enrichment rerank/select`

Goal:
- compute the post-enrichment score and rerank, drop, or hold candidates accordingly

Dependencies:
- Issue 10

Acceptance checks:
- enrich-before and enrich-after ranking changes are explainable
- candidates below enrichment floors are removed
- final selection remains `daily_brief` consumer-specific

Artifacts / outputs:
- rerank reports

### Stream F: Review And Hard Gates

#### Issue 12

Title:
- `[P1] Split briefing review into integrity critic, value gate, and fixed revision routing`

Goal:
- turn review into structured routing and gating instead of free-form critic text

Dependencies:
- Issue 11

Acceptance checks:
- source, freshness, and weak-evidence problems route to enricher
- expression and structure problems route to composer
- low-value or duplicate candidates are dropped

Artifacts / outputs:
- minimal `ReviewIssue` persistence

#### Issue 13

Title:
- `[P1] Add hard gates for claim-evidence binding, numeric checks, freshness, and source floors`

Goal:
- gate the final rendered brief artifact with explicit claim, numeric, freshness, and source-floor checks

Dependencies:
- Issue 12

Acceptance checks:
- key claims bind to explicit evidence
- numeric, time, price, and guidance claims are checkable
- the final rendered artifact, not just intermediate sections, is gated

Artifacts / outputs:
- final artifact gate outputs

### Stream G: Primary Cutover

#### Issue 14

Title:
- `[P1] Promote issue discovery v0 from shadow to primary for daily brief`

Goal:
- switch the new selector to authoritative status only after rollout thresholds are met

Dependencies:
- Issue 13

Acceptance checks:
- citation validation does not regress
- renderer compatibility does not regress
- selected issues show fewer duplicates and headline clusters
- analyst preference beats the baseline

Artifacts / outputs:
- rollout decision record

## Compressed Priority Set

If only the highest-value first batch is needed, start with these eight issues:

1. Add additive schema and artifacts
2. Add OpenBB-backed supplemental market_stream adapter
3. Implement deterministic event clustering v0
4. Implement single-event issue candidate builder v0
5. Implement discovery-score feature extraction
6. Build shortlist selector v0 with `issue_dedup` reuse
7. Add shadow mode and dual-path comparison
8. Add selector evals and rollout checks

This batch is enough to answer the core Phase 1 question:

- can the new discovery path select better issues than the current baseline

## Issue Template

Every child issue should use this shape:

- `Goal`
- `Why now`
- `In scope`
- `Out of scope`
- `Dependencies`
- `Acceptance checks`
- `Artifacts / outputs`
- `Rollout notes`

## Full Template: Issue 2

Title:
- `[P1] Add OpenBB-backed market data adapter for supplemental market_stream inputs`

Goal:
- add an optional OpenBB-backed adapter that supplies structured market data to `market_stream` as supplemental inputs

Why now:
- improve market linkage and market snapshot quality early, without changing the core news-first proof path for selector quality

In scope:
- narrow dataset whitelist only
- adapter interface and normalization
- feature flag, disabled by default
- artifact writing for OpenBB-derived inputs
- graceful failure when OpenBB is unavailable

Out of scope:
- broad OpenBB surface area
- replacing canonical-news-item clustering
- making OpenBB authoritative for selector quality evaluation before shadow proof exists
- alert-policy redesign

Dependencies:
- hard: Issue 1
- recommended sequencing: before Issue 3
- if it lands later, it must still remain supplemental and non-blocking

Acceptance checks:
- configured OpenBB datasets can be fetched and normalized
- baseline mode remains unchanged when the flag is off
- supplemental artifacts are written deterministically
- failures degrade cleanly without breaking `market_stream`

Artifacts / outputs:
- `openbb_market_inputs.json`
- `openbb_adapter_report.json`
- optional market snapshot augmentation fields

Rollout notes:
- feature-flagged only
- supplemental only
- do not let OpenBB become the reason the selector appears better during the first shadow proof
