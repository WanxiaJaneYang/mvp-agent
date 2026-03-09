# M002 Ingestion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first ingestion/runtime primitives for fetch planning, extraction, normalization, and deduplication with paywall-safe metadata handling.

**Architecture:** Keep the ingestion layer deterministic and DB-agnostic. The modules will transform source definitions plus provided payloads into normalized `documents`-compatible dictionaries, so future network and persistence work can plug in without changing the contract.

**Tech Stack:** Python 3.11+, `dataclasses`, `hashlib`, `unittest`

---

### Task 1: Add cap-enforcement fetch planner

**Files:**
- Create: `apps/agent/ingest/fetch.py`
- Create: `tests/agent/ingest/test_fetch.py`

**Step 1: Write the failing test**

Add tests that verify:
- per-source cap truncates candidate items
- global cap truncates the combined result

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.ingest.test_fetch -v`
Expected: FAIL because `apps.agent.ingest.fetch` does not exist.

**Step 3: Write minimal implementation**

Add a small planner that takes source definitions plus candidate payload lists and returns selected items within configured caps.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.ingest.test_fetch -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/ingest/fetch.py tests/agent/ingest/test_fetch.py
git commit -m "feat(ingest): add source fetch planning with caps"
```

### Task 2: Add extraction helpers

**Files:**
- Create: `apps/agent/ingest/extract.py`
- Create: `tests/agent/ingest/test_extract.py`

**Step 1: Write the failing test**

Add one RSS extraction test and one HTML extraction test that assert required metadata fields are preserved in a common intermediate shape.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.ingest.test_extract -v`
Expected: FAIL because extraction helpers do not exist.

**Step 3: Write minimal implementation**

Add extraction helpers for the first two source types used in the model: `rss` and `html`.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.ingest.test_extract -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/ingest/extract.py tests/agent/ingest/test_extract.py
git commit -m "feat(ingest): add rss and html extraction helpers"
```

### Task 3: Add normalization with metadata-only paywall handling

**Files:**
- Create: `apps/agent/ingest/normalize.py`
- Create: `tests/agent/ingest/test_normalize.py`

**Step 1: Write the failing test**

Add tests asserting:
- normalized records match the `documents` contract shape
- `metadata_only` sources force `body_text = None`
- `full` sources preserve provided body text

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.ingest.test_normalize -v`
Expected: FAIL because normalization helpers do not exist.

**Step 3: Write minimal implementation**

Add a normalizer that:
- maps source + extracted payload to document fields
- computes content hash
- preserves paywall-safe metadata

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.ingest.test_normalize -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/ingest/normalize.py tests/agent/ingest/test_normalize.py
git commit -m "feat(ingest): add paywall-safe document normalization"
```

### Task 4: Add dedup helpers

**Files:**
- Create: `apps/agent/ingest/dedup.py`
- Create: `tests/agent/ingest/test_dedup.py`

**Step 1: Write the failing test**

Add tests asserting duplicate detection by:
- canonical URL
- content hash

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.ingest.test_dedup -v`
Expected: FAIL because dedup helpers do not exist.

**Step 3: Write minimal implementation**

Add exact-match dedup helpers for URL and hash plus a simple duplicate classification helper.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.ingest.test_dedup -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/ingest/dedup.py tests/agent/ingest/test_dedup.py
git commit -m "feat(ingest): add exact dedup helpers"
```

### Task 5: Full verification and progress logging

**Files:**
- Modify: `claude-progress.txt`

**Step 1: Update progress log**

Append the ingestion-skeleton summary, validation commands, and next step to `claude-progress.txt`.

**Step 2: Run verification**

Run:
- `python -m unittest tests.agent.ingest.test_fetch -v`
- `python -m unittest tests.agent.ingest.test_extract -v`
- `python -m unittest tests.agent.ingest.test_normalize -v`
- `python -m unittest tests.agent.ingest.test_dedup -v`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `python -m compileall -q apps tests scripts evals`

Expected:
- ingestion tests PASS
- full suite PASS
- compile check PASS

**Step 3: Commit**

```bash
git add claude-progress.txt
git commit -m "docs: log ingestion skeleton progress"
```
