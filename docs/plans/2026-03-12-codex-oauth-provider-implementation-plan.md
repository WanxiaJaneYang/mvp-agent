# Codex OAuth Provider Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `codex-oauth` daily-brief provider path that uses local `codex login` / ChatGPT-backed authentication instead of `OPENAI_API_KEY`, while preserving the existing issue-planner and claim-composer JSON contracts.

**Architecture:** Keep the deterministic evidence layer unchanged. Add a provider registry that can resolve `deterministic`, `openai`, and `codex-oauth`. Implement a Codex CLI runtime adapter that shells out to `codex exec`, captures strict JSON output, and reuses the existing issue-planner and claim-composer parsers and validators.

**Tech Stack:** Python 3.11+, `argparse`, `subprocess`, existing daily-brief provider interfaces, `unittest`, `ruff`, `mypy`.

---

## Child Issue Map

- Child issue A: provider registry and runner wiring
- Child issue B: Codex OAuth runtime adapter
- Child issue C: tests, README, and demo path

The child issues should have disjoint primary write scopes.

### Task 1: Provider Registry and Runner Wiring

**Files:**
- Create: `apps/agent/daily_brief/provider_registry.py`
- Modify: `scripts/run_daily_brief_fixture.py`
- Modify: `scripts/run_daily_brief.py`
- Test: `tests/agent/daily_brief/test_provider_registry.py`

**Step 1: Write the failing test**

```python
def test_build_daily_brief_providers_resolves_codex_oauth():
    planner, composer = build_daily_brief_providers(
        provider="codex-oauth",
        codex_runner=fake_runner,
    )
    assert planner is not None
    assert composer is not None
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.agent.daily_brief.test_provider_registry -v`
Expected: FAIL because the provider registry does not exist yet.

**Step 3: Write minimal implementation**

Implement a provider registry helper that:
- accepts `provider`
- returns `(issue_planner, claim_composer)`
- dispatches to deterministic / OpenAI / Codex builder functions
- keeps provider-specific config validation out of runner scripts

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.agent.daily_brief.test_provider_registry -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/provider_registry.py scripts/run_daily_brief_fixture.py scripts/run_daily_brief.py tests/agent/daily_brief/test_provider_registry.py
git commit -m "feat: add daily brief provider registry"
```

### Task 2: Codex OAuth Runtime Adapter

**Files:**
- Create: `apps/agent/daily_brief/codex_runtime.py`
- Modify: `apps/agent/daily_brief/openai_issue_planner.py`
- Modify: `apps/agent/daily_brief/openai_claim_composer.py`
- Test: `tests/agent/daily_brief/test_codex_runtime.py`

**Step 1: Write the failing tests**

```python
def test_build_codex_daily_brief_providers_requires_logged_in_codex():
    with self.assertRaises(ValueError):
        build_codex_daily_brief_providers(codex_runner=fake_runner, login_checker=lambda: False)


def test_codex_exec_runtime_returns_json_message():
    runtime = CodexExecJsonClient(runner=fake_runner)
    payload = runtime.create_json_response({"messages": [...], "response_format": {...}})
    self.assertEqual(payload, '[{"issue_id": "issue_001"}]')
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.agent.daily_brief.test_codex_runtime -v`
Expected: FAIL because the Codex runtime adapter does not exist yet.

**Step 3: Write minimal implementation**

Implement:
- `build_codex_daily_brief_providers(...)`
- login/CLI checks using bounded helper functions
- `CodexExecJsonClient` that:
  - builds a strict JSON-only prompt from the request payload
  - runs `codex exec` non-interactively
  - captures the last assistant message
  - returns JSON text for existing parsers

Do not change issue-map or claim-object schemas.

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.agent.daily_brief.test_codex_runtime -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/agent/daily_brief/codex_runtime.py apps/agent/daily_brief/openai_issue_planner.py apps/agent/daily_brief/openai_claim_composer.py tests/agent/daily_brief/test_codex_runtime.py
git commit -m "feat: add codex oauth daily brief runtime"
```

### Task 3: Script Flags, README, and Runner Coverage

**Files:**
- Modify: `scripts/run_daily_brief_fixture.py`
- Modify: `scripts/run_daily_brief.py`
- Modify: `README.md`
- Modify: `tests/agent/daily_brief/test_runner.py`
- Modify: `tests/agent/daily_brief/test_openai_runtime.py`
- Test: `tests/agent/daily_brief/test_provider_registry.py`
- Test: `tests/agent/daily_brief/test_codex_runtime.py`

**Step 1: Write the failing tests**

```python
def test_fixture_script_accepts_codex_oauth_provider():
    result = parse_args(["--provider", "codex-oauth"])
    assert result.provider == "codex-oauth"
```

```python
def test_run_fixture_daily_brief_forwards_codex_provider():
    result = run_fixture_daily_brief(..., issue_planner=fake_planner, claim_composer=fake_composer)
    assert result["status"] in {"ok", "abstained"}
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.agent.daily_brief.test_runner tests.agent.daily_brief.test_provider_registry tests.agent.daily_brief.test_codex_runtime -v`
Expected: FAIL until script choices and wiring are updated.

**Step 3: Write minimal implementation**

Update scripts and docs so that:
- `--provider codex-oauth` is accepted
- OpenAI-only wording is removed from provider selection help text
- README documents:
  - `codex login`
  - `codex login status`
  - fixture command for `codex-oauth`
  - current differences between `openai` and `codex-oauth`

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.agent.daily_brief.test_runner tests.agent.daily_brief.test_provider_registry tests.agent.daily_brief.test_codex_runtime -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/run_daily_brief_fixture.py scripts/run_daily_brief.py README.md tests/agent/daily_brief/test_runner.py tests/agent/daily_brief/test_provider_registry.py tests/agent/daily_brief/test_codex_runtime.py
git commit -m "docs: wire codex oauth provider into runners"
```

### Task 4: Full Verification and Demo Smoke

**Files:**
- Modify: none unless verification reveals a bug

**Step 1: Run focused validation**

Run:
- `python -m unittest tests.agent.daily_brief.test_provider_registry tests.agent.daily_brief.test_codex_runtime tests.agent.daily_brief.test_runner -v`
- `python -m ruff check apps/agent/daily_brief/codex_runtime.py apps/agent/daily_brief/provider_registry.py scripts/run_daily_brief.py scripts/run_daily_brief_fixture.py tests/agent/daily_brief/test_provider_registry.py tests/agent/daily_brief/test_codex_runtime.py`
- `python -m mypy apps`

Expected: all pass

**Step 2: Run repo validation**

Run:
- `python scripts/validate_artifacts.py`
- `python scripts/validate_decision_record_schema.py`
- `python -m compileall -q apps tests scripts`

Expected: all pass

**Step 3: Run local Codex OAuth demo smoke**

Run:

```bash
python scripts/run_daily_brief_fixture.py --provider codex-oauth --base-dir .tmp_codex_oauth_demo
```

Expected:
- run reaches the model layer without `OPENAI_API_KEY`
- if local Codex login exists, the run returns `ok` or a validator-driven abstain
- if local Codex login is missing, the failure is explicit and provider-specific

**Step 4: Commit if verification required fixes**

```bash
git add ...
git commit -m "fix: stabilize codex oauth demo path"
```

## Execution Notes

- Keep transport-specific logic inside provider/runtime modules.
- Do not move citation validation into provider code.
- Do not persist Codex auth artifacts or tokens.
- If a live `codex exec` smoke run fails due to CLI/runtime behavior, open a follow-on bug issue instead of patching around the failure silently.
