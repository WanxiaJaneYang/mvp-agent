# Issue #36 Daily Brief Vertical Slice Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first deterministic daily-brief runner that turns the v1 active source subset fixture payloads into JSON row artifacts, a validated HTML brief, and a schema-valid decision record.

**Architecture:** Add a narrow `daily_brief` runtime package that loads the active subset and committed fixture payloads, derives a deterministic topic query, reuses the existing ingest/retrieval/validation helpers, and writes SQLite-compatible artifact rows. Pair it with a small HTML renderer in `apps/agent/delivery`, and expose one runnable script entrypoint for the local vertical slice.

**Tech Stack:** Python 3.11+, `json`, `pathlib`, `tempfile`, `unittest`, existing repo helpers in `apps.agent.ingest`, `apps.agent.retrieval`, `apps.agent.validators`, and `apps.agent.pipeline`

---

### Task 1: Scaffold deterministic fixtures and topic-selection helpers

**Files:**
- Create: `artifacts/runtime/daily_brief_fixture_payloads.json`
- Create: `apps/agent/daily_brief/__init__.py`
- Create: `apps/agent/daily_brief/runner.py`
- Create: `tests/agent/daily_brief/test_runner.py`

**Step 1: Write the failing test**

Add tests asserting:
- fixture payloads load by `source_id`
- only the active v1 subset is selected
- the topic/query builder derives a deterministic query from the ingested documents

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_runner -v`
Expected: FAIL because `apps.agent.daily_brief.runner` and the fixture payload artifact do not exist yet.

**Step 3: Write minimal implementation**

Implement:
- fixture loading from `artifacts/runtime/daily_brief_fixture_payloads.json`
- active-source resolution via `load_active_source_subset()`
- a deterministic query/topic helper in `apps/agent/daily_brief/runner.py`

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_runner -v`
Expected: PASS for fixture loading and query selection coverage.

**Step 5: Commit**

```bash
git add artifacts/runtime/daily_brief_fixture_payloads.json apps/agent/daily_brief/__init__.py apps/agent/daily_brief/runner.py tests/agent/daily_brief/test_runner.py
git commit -m "feat(daily-brief): scaffold deterministic fixture loading"
```

### Task 2: Add deterministic synthesis and citation builders

**Files:**
- Create: `apps/agent/daily_brief/synthesis.py`
- Create: `tests/agent/daily_brief/test_synthesis.py`
- Modify: `apps/agent/daily_brief/runner.py`

**Step 1: Write the failing test**

Add tests asserting:
- evidence-pack rows can be transformed into `prevailing`, `counter`, `minority`, and `watch` bullets
- citation rows are created with stable IDs and paywall-safe fields
- metadata-only sources fall back to snippet-style citation content rather than fabricated quotes

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_synthesis -v`
Expected: FAIL because the synthesis builder and citation helpers do not exist yet.

**Step 3: Write minimal implementation**

Implement:
- deterministic section assignment from evidence-pack rows
- synthesis bullet construction with citation IDs
- citation-row construction aligned to the current decision-record and validation contracts

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_synthesis -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/synthesis.py apps/agent/daily_brief/runner.py tests/agent/daily_brief/test_synthesis.py
git commit -m "feat(daily-brief): add deterministic synthesis builder"
```

### Task 3: Add the local HTML renderer

**Files:**
- Create: `apps/agent/delivery/__init__.py`
- Create: `apps/agent/delivery/html_report.py`
- Create: `tests/agent/delivery/test_html_report.py`

**Step 1: Write the failing test**

Add tests asserting:
- HTML output includes the run title/date and the core brief sections
- rendered bullets include citation labels or links
- abstained synthesis renders explicitly rather than looking like a successful brief

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.delivery.test_html_report -v`
Expected: FAIL because the renderer module does not exist yet.

**Step 3: Write minimal implementation**

Implement a small deterministic renderer that:
- accepts validated synthesis plus citation store metadata
- writes a stable HTML document under a caller-provided output path
- keeps formatting simple and inspectable

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.delivery.test_html_report -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/delivery/__init__.py apps/agent/delivery/html_report.py tests/agent/delivery/test_html_report.py
git commit -m "feat(delivery): add local html daily brief renderer"
```

### Task 4: Implement the end-to-end daily-brief runner and artifact persistence

**Files:**
- Modify: `apps/agent/daily_brief/runner.py`
- Modify: `tests/agent/daily_brief/test_runner.py`

**Step 1: Write the failing test**

Extend runner tests to assert the end-to-end slice:
- plans fixture items from active sources
- builds document, chunk, FTS, evidence-pack, citation, and synthesis artifacts
- validates the synthesis
- writes HTML output and a decision record
- returns abstained output when usable evidence is insufficient

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_runner -v`
Expected: FAIL on missing orchestration, artifact writes, or abstain handling.

**Step 3: Write minimal implementation**

Implement:
- end-to-end orchestration through the existing helper modules
- JSON artifact persistence for intermediate row sets
- decision-record persistence via `build_and_persist_decision_record()`
- run summary / counters for fetched docs, ingested docs, and indexed chunks

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_runner -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/runner.py tests/agent/daily_brief/test_runner.py
git commit -m "feat(daily-brief): add executable vertical slice runner"
```

### Task 5: Add the runnable script and finish verification

**Files:**
- Create: `scripts/run_daily_brief_fixture.py`
- Modify: `claude-progress.txt`
- Modify: `progress.md`
- Modify: `task_plan.md`

**Step 1: Write the failing test or smoke assertion**

Add a small runner test or script smoke assertion that verifies a caller can invoke the deterministic path through one stable entrypoint.

**Step 2: Run targeted tests to verify the remaining gap**

Run:
- `python -m unittest tests.agent.daily_brief.test_runner -v`
- `python -m unittest tests.agent.daily_brief.test_synthesis -v`
- `python -m unittest tests.agent.delivery.test_html_report -v`

Expected: PASS after the entrypoint is wired correctly.

**Step 3: Write minimal implementation**

Implement:
- a script entrypoint that runs the deterministic daily-brief slice against the committed fixture bundle
- progress-log updates in `claude-progress.txt`
- planning-file updates reflecting implementation completion and verification evidence

**Step 4: Run full verification**

Run:
- `python scripts/run_daily_brief_fixture.py`
- `python -m unittest tests.agent.daily_brief.test_runner -v`
- `python -m unittest tests.agent.daily_brief.test_synthesis -v`
- `python -m unittest tests.agent.delivery.test_html_report -v`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `python -m compileall -q apps tests scripts evals`

Expected:
- script writes deterministic artifact output successfully
- targeted tests PASS
- full suite PASS
- compile check PASS

**Step 5: Commit**

```bash
git add scripts/run_daily_brief_fixture.py claude-progress.txt progress.md task_plan.md
git commit -m "docs: log daily brief vertical slice progress"
```
