# M003 Retrieval Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first retrieval primitives for chunking full-text documents and producing `chunks` plus `chunks_fts`-compatible rows.

**Architecture:** Keep the retrieval layer deterministic and DB-agnostic. The modules will transform normalized document records into ordered chunk rows and FTS rows, with a minimal in-memory search helper to validate the indexing contract before SQLite integration exists.

**Tech Stack:** Python 3.11+, `dataclasses`, `re`, `unittest`

---

### Task 1: Add chunk splitting for full-text documents

**Files:**
- Create: `apps/agent/retrieval/chunker.py`
- Create: `tests/agent/retrieval/test_chunker.py`

**Step 1: Write the failing test**

Add tests asserting:
- full-text documents are split into stable ordered chunks
- metadata-only documents produce no chunks

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.retrieval.test_chunker -v`
Expected: FAIL because `apps.agent.retrieval.chunker` does not exist.

**Step 3: Write minimal implementation**

Add a deterministic chunker that:
- reads `body_text`
- returns ordered chunk spans with `chunk_index`, `text`, `char_start`, and `char_end`
- skips metadata-only documents

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.retrieval.test_chunker -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/retrieval/chunker.py tests/agent/retrieval/test_chunker.py
git commit -m "feat(retrieval): add deterministic document chunker"
```

### Task 2: Add chunk row builders

**Files:**
- Modify: `apps/agent/retrieval/chunker.py`
- Modify: `tests/agent/retrieval/test_chunker.py`

**Step 1: Write the failing test**

Add tests asserting chunk rows:
- preserve stable `chunk_index`
- include `doc_id`, `token_count`, `char_start`, `char_end`, and `created_at`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.retrieval.test_chunker -v`
Expected: FAIL because row-building helpers do not exist yet.

**Step 3: Write minimal implementation**

Add a row builder that converts chunk spans into `chunks`-compatible dictionaries.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.retrieval.test_chunker -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/retrieval/chunker.py tests/agent/retrieval/test_chunker.py
git commit -m "feat(retrieval): add chunk row builders"
```

### Task 3: Add FTS row builders and in-memory search helper

**Files:**
- Create: `apps/agent/retrieval/fts_index.py`
- Create: `tests/agent/retrieval/test_fts_index.py`

**Step 1: Write the failing test**

Add tests asserting:
- `chunks_fts` rows mirror the expected fields
- keyword lookup returns matching chunks in descending relevance order

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.retrieval.test_fts_index -v`
Expected: FAIL because FTS helpers do not exist.

**Step 3: Write minimal implementation**

Add helpers that:
- validate incoming chunk rows
- build `chunks_fts` row dictionaries
- perform a simple lowercase term-frequency search for tests

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.retrieval.test_fts_index -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/retrieval/fts_index.py tests/agent/retrieval/test_fts_index.py
git commit -m "feat(retrieval): add fts row builders and keyword search"
```

### Task 4: Add hard-fail behavior for invalid index rows

**Files:**
- Modify: `apps/agent/retrieval/fts_index.py`
- Modify: `tests/agent/retrieval/test_fts_index.py`

**Step 1: Write the failing test**

Add tests asserting invalid rows raise `ValueError` instead of being silently skipped.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.retrieval.test_fts_index -v`
Expected: FAIL because invalid input is not rejected yet.

**Step 3: Write minimal implementation**

Add explicit validation for required FTS/index fields and raise `ValueError` on invalid rows.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.retrieval.test_fts_index -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/retrieval/fts_index.py tests/agent/retrieval/test_fts_index.py
git commit -m "feat(retrieval): hard-fail invalid index rows"
```

### Task 5: Full verification and progress logging

**Files:**
- Modify: `claude-progress.txt`
- Modify: `artifacts/modelling/backlog.json`

**Step 1: Update progress records**

Append the retrieval-skeleton summary to `claude-progress.txt` and mark `M003` implemented in `artifacts/modelling/backlog.json`.

**Step 2: Run verification**

Run:
- `python -m unittest tests.agent.retrieval.test_chunker -v`
- `python -m unittest tests.agent.retrieval.test_fts_index -v`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `python -m compileall -q apps tests scripts evals`
- `python scripts/validate_artifacts.py`

Expected:
- retrieval tests PASS
- full suite PASS
- compile check PASS
- artifact validation PASS

**Step 3: Commit**

```bash
git add claude-progress.txt artifacts/modelling/backlog.json
git commit -m "docs: log retrieval skeleton progress"
```
