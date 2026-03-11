# Daily Brief Model-Layer Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current section-bullet daily-brief synthesis path with a provider-agnostic, OpenAI-first issue-planner and claim-composer pipeline built on top of the existing deterministic evidence layer.

**Architecture:** Keep ingestion, retrieval, citation store, and budget guard deterministic. Introduce two task-specific model adapters, structured issue/claim schemas, deterministic rule validation, optional critic hooks, and a renderer that consumes structured issues and claims instead of thin bullet lists.

**Tech Stack:** Python 3.11+, `unittest`, provider-agnostic model adapter layer, OpenAI as first provider

---

### Task 1: Add structured issue and claim contracts

**Files:**
- Modify: `apps/agent/pipeline/types.py`
- Create: `tests/agent/pipeline/test_daily_brief_types.py`

**Step 1: Write the failing test**

Add tests for:
- `IssueMap`-style structured objects
- `ClaimObject`-style structured objects
- `DailyBriefSynthesisV2`-style issue grouping
- allowed novelty labels

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.pipeline.test_daily_brief_types -v`
Expected: FAIL because the richer issue/claim contracts do not exist yet.

**Step 3: Write minimal implementation**

Add typed dataclasses/enums for:
- issue map
- claim object
- novelty label
- claim kind

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.pipeline.test_daily_brief_types -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/pipeline/types.py tests/agent/pipeline/test_daily_brief_types.py
git commit -m "feat(types): add issue and claim contracts for daily briefs"
```

### Task 2: Add provider-agnostic model interfaces

**Files:**
- Create: `apps/agent/daily_brief/model_interfaces.py`
- Create: `tests/agent/daily_brief/test_model_interfaces.py`

**Step 1: Write the failing test**

Add tests asserting the provider layer exposes task-specific interfaces:
- `IssuePlannerProvider`
- `ClaimComposerProvider`

Do not build a generic all-purpose LLM client.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_model_interfaces -v`
Expected: FAIL because the provider interfaces do not exist.

**Step 3: Write minimal implementation**

Add narrow provider protocols or ABCs with structured input/output contracts.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_model_interfaces -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/model_interfaces.py tests/agent/daily_brief/test_model_interfaces.py
git commit -m "feat(daily-brief): add provider-agnostic model interfaces"
```

### Task 3: Add OpenAI-first issue planner adapter

**Files:**
- Create: `apps/agent/daily_brief/openai_issue_planner.py`
- Create: `tests/agent/daily_brief/test_openai_issue_planner.py`

**Step 1: Write the failing test**

Add tests asserting the OpenAI issue planner:
- accepts deterministic evidence-pack input
- returns schema-valid issue map JSON
- rejects malformed provider output

Mock the provider boundary only; do not make network calls in unit tests.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_openai_issue_planner -v`
Expected: FAIL because the adapter does not exist.

**Step 3: Write minimal implementation**

Implement the OpenAI-first issue planner adapter with:
- structured prompt assembly
- schema parsing
- malformed-output handling

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_openai_issue_planner -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/openai_issue_planner.py tests/agent/daily_brief/test_openai_issue_planner.py
git commit -m "feat(daily-brief): add OpenAI issue planner adapter"
```

### Task 4: Add OpenAI-first claim composer adapter

**Files:**
- Create: `apps/agent/daily_brief/openai_claim_composer.py`
- Create: `tests/agent/daily_brief/test_openai_claim_composer.py`

**Step 1: Write the failing test**

Add tests asserting the claim composer:
- consumes issue map + citation store + prior brief context
- returns schema-valid claim objects
- includes `why_it_matters` and `novelty_vs_prior_brief`
- rejects malformed provider output

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_openai_claim_composer -v`
Expected: FAIL because the adapter does not exist.

**Step 3: Write minimal implementation**

Implement the OpenAI-first claim composer adapter with schema validation and bounded error handling.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_openai_claim_composer -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/openai_claim_composer.py tests/agent/daily_brief/test_openai_claim_composer.py
git commit -m "feat(daily-brief): add OpenAI claim composer adapter"
```

### Task 5: Add deterministic prior-brief context builder

**Files:**
- Create: `apps/agent/daily_brief/prior_brief_context.py`
- Create: `tests/agent/daily_brief/test_prior_brief_context.py`

**Step 1: Write the failing test**

Add tests asserting the prior-brief builder extracts bounded context for:
- prior issue questions
- prior claim summaries
- prior timestamps
- prior citation/source references

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_prior_brief_context -v`
Expected: FAIL because the context builder does not exist.

**Step 3: Write minimal implementation**

Add a deterministic helper that reads prior brief artifacts and emits bounded comparison context.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_prior_brief_context -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/prior_brief_context.py tests/agent/daily_brief/test_prior_brief_context.py
git commit -m "feat(daily-brief): add prior brief context builder"
```

### Task 6: Replace current synthesis path with issue planner + claim composer orchestration

**Files:**
- Modify: `apps/agent/daily_brief/runner.py`
- Modify: `apps/agent/daily_brief/synthesis.py`
- Modify: `tests/agent/daily_brief/test_runner.py`
- Modify: `tests/agent/daily_brief/test_synthesis.py`

**Step 1: Write the failing test**

Add tests asserting the daily-brief path now:
- invokes issue planning before claim composition
- produces issue-question-centered outputs
- does not collapse the day into one vague global query result
- can still abstain cleanly when issue planning or claim composition yields nothing usable

**Step 2: Run test to verify it fails**

Run:
- `python -m unittest tests.agent.daily_brief.test_runner -v`
- `python -m unittest tests.agent.daily_brief.test_synthesis -v`

Expected: FAIL because the current synthesis path still directly builds section bullets.

**Step 3: Write minimal implementation**

Refactor the daily-brief path so:
- current deterministic evidence building stays
- issue planner output becomes the first analysis artifact
- claim composer output becomes the second analysis artifact
- existing flat section synthesis is removed or converted into a legacy fallback only if necessary during migration

**Step 4: Run test to verify it passes**

Run:
- `python -m unittest tests.agent.daily_brief.test_runner -v`
- `python -m unittest tests.agent.daily_brief.test_synthesis -v`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/runner.py apps/agent/daily_brief/synthesis.py tests/agent/daily_brief/test_runner.py tests/agent/daily_brief/test_synthesis.py
git commit -m "feat(daily-brief): orchestrate issue planning and claim composition"
```

### Task 7: Upgrade deterministic validator to validate issue and claim objects

**Files:**
- Modify: `apps/agent/validators/citation_validator.py`
- Modify: `apps/agent/pipeline/stage8_validation.py`
- Modify: `tests/agent/validators/test_citation_validator.py`
- Modify: `tests/agent/pipeline/test_stage8_validation.py`

**Step 1: Write the failing test**

Add tests for:
- claim-level citation coverage
- issue consistency
- numeric/date claim support strength
- support/opposition mapping on claim objects

**Step 2: Run test to verify it fails**

Run:
- `python -m unittest tests.agent.validators.test_citation_validator -v`
- `python -m unittest tests.agent.pipeline.test_stage8_validation -v`

Expected: FAIL because current validation still assumes thinner section/bullet structures.

**Step 3: Write minimal implementation**

Extend stage 8 validation to understand structured issues and claims while preserving bounded retry behavior.

**Step 4: Run test to verify it passes**

Run:
- `python -m unittest tests.agent.validators.test_citation_validator -v`
- `python -m unittest tests.agent.pipeline.test_stage8_validation -v`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/validators/citation_validator.py apps/agent/pipeline/stage8_validation.py tests/agent/validators/test_citation_validator.py tests/agent/pipeline/test_stage8_validation.py
git commit -m "feat(validation): validate issue and claim objects"
```

### Task 8: Add optional critic contract and local integration point

**Files:**
- Create: `apps/agent/daily_brief/critic.py`
- Create: `tests/agent/daily_brief/test_critic.py`
- Modify: `apps/agent/daily_brief/runner.py`

**Step 1: Write the failing test**

Add tests asserting critic output is structured and can flag:
- source-by-source paraphrase
- thesis mismatch
- empty `why_it_matters`

The critic should not rewrite claims.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_critic -v`
Expected: FAIL because the critic contract does not exist.

**Step 3: Write minimal implementation**

Add a small critic interface and runner integration point. It can be no-op or disabled by default, but the contract must exist.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_critic -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/critic.py tests/agent/daily_brief/test_critic.py apps/agent/daily_brief/runner.py
git commit -m "feat(daily-brief): add critic contract for structured claims"
```

### Task 9: Update renderer and decision-record persistence to consume structured claims

**Files:**
- Modify: `apps/agent/delivery/html_report.py`
- Modify: `apps/agent/pipeline/stage10_decision_record.py`
- Modify: `tests/agent/delivery/test_html_report.py`
- Modify: `tests/agent/pipeline/test_stage10_decision_record.py`

**Step 1: Write the failing test**

Add tests asserting renderer and decision record consume:
- issue question
- issue summary
- claim objects by kind
- why it matters
- novelty labels

**Step 2: Run test to verify it fails**

Run:
- `python -m unittest tests.agent.delivery.test_html_report -v`
- `python -m unittest tests.agent.pipeline.test_stage10_decision_record -v`

Expected: FAIL because current rendering/persistence still reflect thinner intermediate objects.

**Step 3: Write minimal implementation**

Update renderer and persistence helpers to work from issue/claim structures directly.

**Step 4: Run test to verify it passes**

Run:
- `python -m unittest tests.agent.delivery.test_html_report -v`
- `python -m unittest tests.agent.pipeline.test_stage10_decision_record -v`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/delivery/html_report.py apps/agent/pipeline/stage10_decision_record.py tests/agent/delivery/test_html_report.py tests/agent/pipeline/test_stage10_decision_record.py
git commit -m "feat(delivery): render and persist structured issue claims"
```

### Task 10: Update modelling and docs to reflect the redesigned pipeline

**Files:**
- Modify: `artifacts/modelling/pipeline.md`
- Modify: `artifacts/modelling/citation_contract.md`
- Modify: `README.md`

**Step 1: Write doc updates**

Document:
- issue planner stage
- claim composer stage
- provider-agnostic / OpenAI-first strategy
- structured claim validation

**Step 2: Run artifact validation**

Run: `python scripts/validate_artifacts.py`
Expected: PASS

**Step 3: Commit**

```bash
git add artifacts/modelling/pipeline.md artifacts/modelling/citation_contract.md README.md
git commit -m "docs(daily-brief): document model-layer redesign"
```

### Task 11: Full verification

**Files:**
- No new source edits expected

**Step 1: Run targeted suites**

Run:
- `python -m unittest tests.agent.daily_brief.test_model_interfaces -v`
- `python -m unittest tests.agent.daily_brief.test_openai_issue_planner -v`
- `python -m unittest tests.agent.daily_brief.test_openai_claim_composer -v`
- `python -m unittest tests.agent.daily_brief.test_prior_brief_context -v`
- `python -m unittest tests.agent.daily_brief.test_runner -v`
- `python -m unittest tests.agent.validators.test_citation_validator -v`
- `python -m unittest tests.agent.delivery.test_html_report -v`

Expected: PASS

**Step 2: Run repo-level verification**

Run:
- `python scripts/validate_artifacts.py`
- `python scripts/validate_decision_record_schema.py`
- `python -m compileall -q apps tests scripts evals`
- `python -m unittest discover -s tests -p "test_*.py" -v`
- `python -m unittest tests.evals.test_run_eval_suite -v`

Expected:
- validators PASS
- compile PASS
- full suite PASS
- eval suite PASS

**Step 3: Commit**

```bash
git add .
git commit -m "feat(daily-brief): redesign pipeline around issue planning and claim composition"
```
