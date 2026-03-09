# Issue #41 Evidence-Pack Retrieval Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a deterministic evidence-pack retrieval helper that ranks indexed chunk rows, caps final pack size, and emits evidence-pack-item-compatible rows.

**Architecture:** Add a narrow retrieval module downstream of FTS row generation. Keep it in-memory and deterministic so it can validate the evidence-pack contract before SQLite persistence or broader Stage 6 diversity logic exists.

**Tech Stack:** Python 3.11+, `datetime`, `math`, `unittest`

---

### Task 1: Add evidence-pack ordering tests

**Files:**
- Create: `tests/agent/retrieval/test_evidence_pack.py`

**Step 1: Write the failing test**

Add tests asserting:
- stronger text relevance ranks ahead of weaker relevance
- bounded result size truncates the final pack
- ties resolve deterministically

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.retrieval.test_evidence_pack -v`
Expected: FAIL because `apps.agent.retrieval.evidence_pack` does not exist.

**Step 3: Write minimal implementation shape**

Create a module stub with a public function:

```python
def build_evidence_pack(*, fts_rows, query_text, pack_size=30):
    raise NotImplementedError
```

**Step 4: Run test to verify it still fails for missing behavior**

Run: `python -m unittest tests.agent.retrieval.test_evidence_pack -v`
Expected: FAIL on `NotImplementedError` or assertion mismatch rather than import failure.

**Step 5: Commit**

```bash
git add tests/agent/retrieval/test_evidence_pack.py apps/agent/retrieval/evidence_pack.py
git commit -m "test(retrieval): scaffold evidence pack retrieval coverage"
```

### Task 2: Implement scoring and bounded pack assembly

**Files:**
- Create: `apps/agent/retrieval/evidence_pack.py`
- Modify: `tests/agent/retrieval/test_evidence_pack.py`

**Step 1: Write the next failing test**

Add a test asserting:
- the output row contains `source_id`, `publisher`, `credibility_tier`, `retrieval_score`, `semantic_score`, `recency_score`, `credibility_score`, and `rank_in_pack`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.retrieval.test_evidence_pack -v`
Expected: FAIL because output rows do not yet match the evidence-pack-item contract.

**Step 3: Write minimal implementation**

Implement:
- query token counting
- recency normalization from `published_at`
- credibility score mapping
- deterministic sort and truncation
- evidence-pack-item-compatible output rows

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.retrieval.test_evidence_pack -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/retrieval/evidence_pack.py tests/agent/retrieval/test_evidence_pack.py
git commit -m "feat(retrieval): add evidence pack retrieval helper"
```

### Task 3: Add defensive validation

**Files:**
- Modify: `apps/agent/retrieval/evidence_pack.py`
- Modify: `tests/agent/retrieval/test_evidence_pack.py`

**Step 1: Write the failing test**

Add tests asserting:
- missing required row fields raise `ValueError`
- unsupported credibility tiers raise `ValueError`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.retrieval.test_evidence_pack -v`
Expected: FAIL because validation is incomplete.

**Step 3: Write minimal implementation**

Add row validation helpers for required fields, timestamp parsing, and supported tier mapping.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.retrieval.test_evidence_pack -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/retrieval/evidence_pack.py tests/agent/retrieval/test_evidence_pack.py
git commit -m "feat(retrieval): validate evidence pack inputs"
```

### Task 4: Full verification and progress logging

**Files:**
- Modify: `claude-progress.txt`

**Step 1: Update progress log**

Append the evidence-pack retrieval summary, validation commands, and next step to `claude-progress.txt`.

**Step 2: Run verification**

Run:
- `python -m unittest tests.agent.retrieval.test_evidence_pack -v`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `python -m compileall -q apps tests scripts evals`

Expected:
- evidence-pack tests PASS
- full suite PASS
- compile check PASS

**Step 3: Commit**

```bash
git add claude-progress.txt
git commit -m "docs: log evidence pack retrieval progress"
```

