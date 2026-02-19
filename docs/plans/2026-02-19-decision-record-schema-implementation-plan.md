# Decision Record Schema Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement P0 decision-record schema artifacts (spec + JSON example + field-level validation rules) and mark P0 schema definition complete in modelling tracking docs.

**Architecture:** Keep this phase documentation-first and file-first. Introduce a dedicated modelling artifact for the decision record contract, include a canonical JSON example in-repo, and enforce consistency through a lightweight validator script that checks required fields and key conditional rules. Defer pipeline wiring to the next P0 task.

**Tech Stack:** Markdown docs, JSON artifacts, Python 3 unittest + lightweight script validation

---

### Task 1: Add decision-record modelling artifact

**Files:**
- Create: `artifacts/modelling/decision_record_schema.md`

**Step 1: Write the file content with schema contract**

Include:
- purpose and scope (`daily_brief`, `alert`)
- storage path format: `artifacts/decision_records/<YYYY-MM-DD>/<run_id>.json`
- required fields and enums
- claim/rejected-alternatives/budget/guardrail/artifact/rationale sections
- conditional validation rules (supported claims require citations, abstained requires uncertainties, etc.)

**Step 2: Verify file exists and is readable**

Run: `Get-Content artifacts\modelling\decision_record_schema.md`  
Expected: markdown displays with required sections.

**Step 3: Commit**

```bash
git add artifacts/modelling/decision_record_schema.md
git commit -m "docs(modelling): add decision_record schema artifact"
```

### Task 2: Add canonical JSON example

**Files:**
- Create: `artifacts/modelling/examples/decision_record_v1.example.json`

**Step 1: Add valid example payload**

Ensure example matches schema:
- `schema_version: decision_record.v1`
- valid `run_type`
- valid `status`
- at least one supported claim with non-empty `citation_ids`
- structured `budget_snapshot` and `guardrail_checks`

**Step 2: Verify JSON parses**

Run:
`python -c "import json; json.load(open('artifacts/modelling/examples/decision_record_v1.example.json', 'r', encoding='utf-8')); print('ok')"`  
Expected: `ok`

**Step 3: Commit**

```bash
git add artifacts/modelling/examples/decision_record_v1.example.json
git commit -m "docs(modelling): add decision_record v1 example"
```

### Task 3: Add schema validation script

**Files:**
- Create: `scripts/validate_decision_record_schema.py`
- Test: `tests/agent/modelling/test_decision_record_schema_validation.py`

**Step 1: Write failing tests first (TDD)**

Add tests for:
- valid example passes
- missing required top-level key fails
- supported claim with empty citations fails
- abstained status with empty uncertainties fails

**Step 2: Run targeted tests to confirm failure**

Run:
`python -m unittest tests.agent.modelling.test_decision_record_schema_validation -v`  
Expected: FAIL (validator not implemented).

**Step 3: Implement validator script**

Implement:
- JSON parse and required key checks
- enum checks for `run_type` and `status`
- conditional rules for claims/abstained/budget flag consistency
- non-zero exit code with clear message on validation errors

**Step 4: Re-run targeted tests**

Run:
`python -m unittest tests.agent.modelling.test_decision_record_schema_validation -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/validate_decision_record_schema.py tests/agent/modelling/test_decision_record_schema_validation.py
git commit -m "test(modelling): validate decision_record schema rules"
```

### Task 4: Integrate validation into CI workflow

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: Add decision-record schema validation step**

Run script in CI:
- `python scripts/validate_decision_record_schema.py`

Place after artifact validation and before tests.

**Step 2: Validate locally**

Run:
- `python scripts/validate_decision_record_schema.py`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Expected: both PASS.

**Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add decision_record schema validation check"
```

### Task 5: Update modelling trackers and progress

**Files:**
- Modify: `artifacts/modelling/TODO.md`
- Modify: `artifacts/modelling/MODELLING_CHECKLIST.md`
- Modify: `claude-progress.txt`

**Step 1: Update TODO**

Mark P0 item as completed:
- `Define decision_record artifact schema and storage location`

Keep next P0 (`wire generation into synthesis pipeline`) open.

**Step 2: Update checklist**

Add explicit line in strengthening tracks:
- `S1) Decision record schema` -> `PASSING`

**Step 3: Append progress session**

Include:
- files changed
- validation commands + outcomes
- next single step (wire decision_record into synthesis pipeline)

**Step 4: Commit**

```bash
git add artifacts/modelling/TODO.md artifacts/modelling/MODELLING_CHECKLIST.md claude-progress.txt
git commit -m "docs: mark decision_record schema P0 complete"
```

### Task 6: Final verification and PR prep

**Files:**
- Modify (if needed): `README.md` (optional mention under modelling artifacts)

**Step 1: Run full verification**

Run:
- `python scripts/validate_artifacts.py`
- `python scripts/validate_decision_record_schema.py`
- `python -m compileall -q apps tests scripts`
- `python -m unittest discover -s tests -p "test_*.py" -v`

Expected: all PASS.

**Step 2: Create MR**

```bash
git push -u origin feat/decision-record-schema
gh pr create --base master --head feat/decision-record-schema --title "docs(modelling): define decision_record schema (P0)" --body "<summary + validation>"
```

**Step 3: Commit (only if additional docs changed in this task)**

```bash
git add README.md
git commit -m "docs: mention decision_record schema artifact"
```
