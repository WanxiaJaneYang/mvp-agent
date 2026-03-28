# Daily Brief Issue-Centric Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the flat daily-brief section output with a deterministic issue-centered literature-review format that groups competing arguments and visible evidence under 2-3 important issues.

**Architecture:** Keep the current deterministic offline runner, evidence pack, and citation store, but change the synthesis contract to emit issue blocks as the primary unit. Update validation, artifact persistence, and HTML rendering together so the daily-brief path remains coherent end to end.

**Tech Stack:** Python 3.11+, `unittest`

---

### Task 1: Add failing synthesis tests for issue-centered output

**Files:**
- Modify: `tests/agent/daily_brief/test_synthesis.py`

**Step 1: Write the failing test**

Add a test asserting `build_synthesis(...)` returns:
- a top-level `issues` list
- one issue title/question
- nested `prevailing`, `counter`, `minority`, and `watch`
- citations that remain attached to the correct issue arguments

Add a second test asserting evidence from unrelated documents is split into 2-3 issues instead of being mixed into one debate.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_synthesis -v`
Expected: FAIL because `build_synthesis(...)` still returns the old flat top-level section shape.

**Step 3: Write minimal implementation**

Modify `apps/agent/daily_brief/synthesis.py` so `build_synthesis(...)` starts returning an issue-centered structure instead of the old flat shape.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_synthesis -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/agent/daily_brief/test_synthesis.py apps/agent/daily_brief/synthesis.py
git commit -m "feat(daily-brief): group synthesis into issue-centered reviews"
```

### Task 2: Add visible evidence support to issue arguments

**Files:**
- Modify: `tests/agent/daily_brief/test_synthesis.py`
- Modify: `apps/agent/daily_brief/synthesis.py`

**Step 1: Write the failing test**

Add a test asserting each argument entry exposes visible evidence metadata, including:
- `citation_id`
- `publisher`
- `published_at`
- quote/snippet support text

Include a paywall case showing metadata-only citations expose snippet support without quote text.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_synthesis -v`
Expected: FAIL because issue arguments do not yet include visible evidence blocks.

**Step 3: Write minimal implementation**

Extend synthesis building to derive argument-local evidence entries from the citation store and attach them to each issue argument.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_synthesis -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/agent/daily_brief/test_synthesis.py apps/agent/daily_brief/synthesis.py
git commit -m "feat(daily-brief): attach visible evidence to issue arguments"
```

### Task 3: Teach validation to handle nested issue-centered synthesis

**Files:**
- Modify: `tests/agent/pipeline/test_stage8_validation.py`
- Modify: `tests/agent/validators/test_citation_validator.py`
- Modify: `apps/agent/pipeline/stage8_validation.py`
- Modify: `apps/agent/validators/citation_validator.py`

**Step 1: Write the failing test**

Add validation tests asserting:
- nested issue arguments are validated for citation coverage
- an issue with unsupported argument bullets degrades correctly
- retry behavior triggers when all issues lose required core debate sections

**Step 2: Run test to verify it fails**

Run:
- `python -m unittest tests.agent.pipeline.test_stage8_validation -v`
- `python -m unittest tests.agent.validators.test_citation_validator -v`

Expected: FAIL because the validator only understands the old flat top-level section layout.

**Step 3: Write minimal implementation**

Update validator and stage-8 integration so they can:
- traverse issue-centered synthesis
- validate nested `prevailing`, `counter`, `minority`, and `watch`
- preserve issue context in degraded output

Prefer a small normalization layer over duplicating validation logic.

**Step 4: Run test to verify it passes**

Run:
- `python -m unittest tests.agent.pipeline.test_stage8_validation -v`
- `python -m unittest tests.agent.validators.test_citation_validator -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/agent/pipeline/test_stage8_validation.py tests/agent/validators/test_citation_validator.py apps/agent/pipeline/stage8_validation.py apps/agent/validators/citation_validator.py
git commit -m "feat(validation): support issue-centered daily brief synthesis"
```

### Task 4: Update the runner artifact contract for issue metadata

**Files:**
- Modify: `tests/agent/daily_brief/test_runner.py`
- Modify: `apps/agent/daily_brief/runner.py`

**Step 1: Write the failing test**

Extend runner tests to assert:
- `synthesis.json` stores the issue-centered shape
- `synthesis_bullets.json` includes issue identifiers
- `bullet_citations.json` includes issue identifiers
- `run_summary.json` records generated issue count

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_runner -v`
Expected: FAIL because artifact writers still assume flat top-level sections.

**Step 3: Write minimal implementation**

Update runner helpers that serialize synthesis bullets and bullet-citation rows so they include issue-local metadata and can traverse the nested synthesis structure.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_runner -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/agent/daily_brief/test_runner.py apps/agent/daily_brief/runner.py
git commit -m "feat(daily-brief): persist issue-centered runtime artifacts"
```

### Task 5: Render issue-centered literature-review HTML

**Files:**
- Modify: `tests/agent/delivery/test_html_report.py`
- Modify: `apps/agent/delivery/html_report.py`

**Step 1: Write the failing test**

Add renderer tests asserting the HTML output shows:
- issue titles/questions
- issue summaries
- nested `Prevailing`, `Counter`, `Minority`, and `What to Watch`
- visible evidence entries beneath each argument
- citation links that remain usable

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.delivery.test_html_report -v`
Expected: FAIL because the renderer still expects flat top-level sections and does not show argument-local evidence.

**Step 3: Write minimal implementation**

Refactor `render_daily_brief_html(...)` to render issue-centered literature-review blocks using the new synthesis contract.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.delivery.test_html_report -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/agent/delivery/test_html_report.py apps/agent/delivery/html_report.py
git commit -m "feat(delivery): render issue-centered daily brief essays"
```

### Task 6: Update abstain and compatibility behavior

**Files:**
- Modify: `tests/agent/synthesis/test_postprocess.py`
- Modify: `apps/agent/synthesis/postprocess.py`

**Step 1: Write the failing test**

Add tests asserting abstain output remains deterministic under the new issue-centered contract, including the case where no coherent issues survive validation.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.synthesis.test_postprocess -v`
Expected: FAIL because abstain helpers still emit the old flat section shape.

**Step 3: Write minimal implementation**

Update postprocess helpers so abstain output either:
- emits an issue-centered abstain structure, or
- cleanly adapts to the renderer and runner contract chosen for the new daily-brief path

Keep the resulting structure deterministic and explicit.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.synthesis.test_postprocess -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/agent/synthesis/test_postprocess.py apps/agent/synthesis/postprocess.py
git commit -m "feat(synthesis): align abstain path with issue-centered briefs"
```

### Task 7: Update modelling and design docs if executable contracts drift

**Files:**
- Modify: `artifacts/modelling/citation_contract.md`
- Modify: `docs/plans/2026-03-10-issue-36-daily-brief-vertical-slice-design.md`

**Step 1: Document the contract drift**

Update docs so they describe the issue-centered literature-review shape instead of the old single global section set where necessary.

**Step 2: Run artifact/doc verification**

Run: `python scripts/validate_artifacts.py`
Expected: PASS

**Step 3: Commit**

```bash
git add artifacts/modelling/citation_contract.md docs/plans/2026-03-10-issue-36-daily-brief-vertical-slice-design.md
git commit -m "docs(daily-brief): document issue-centered literature review contract"
```

### Task 8: Run full verification

**Files:**
- No source changes expected

**Step 1: Run targeted tests**

Run:
- `python -m unittest tests.agent.daily_brief.test_synthesis -v`
- `python -m unittest tests.agent.daily_brief.test_runner -v`
- `python -m unittest tests.agent.delivery.test_html_report -v`
- `python -m unittest tests.agent.pipeline.test_stage8_validation -v`
- `python -m unittest tests.agent.validators.test_citation_validator -v`
- `python -m unittest tests.agent.synthesis.test_postprocess -v`

Expected: PASS

**Step 2: Run repo-level verification**

Run:
- `python scripts/validate_artifacts.py`
- `python scripts/validate_decision_record_schema.py`
- `python -m compileall -q apps tests scripts evals`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `python -m unittest tests.agent.daily_brief.test_runner tests.agent.daily_brief.test_synthesis tests.agent.delivery.test_html_report -v`
- `python -m unittest tests.evals.test_run_eval_suite -v`

Expected:
- validators PASS
- compile check PASS
- default discovery PASS
- explicitly named daily-brief and delivery suites PASS
- eval suite PASS

**Step 3: Commit**

```bash
git add .
git commit -m "feat(daily-brief): convert vertical slice to issue-centered literature reviews"
```
