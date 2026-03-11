# Codex OAuth Provider Redesign

Issue: `#112`

Date: `2026-03-12`

## Problem

The current daily-brief model path assumes the provider is either:
- fully deterministic, or
- OpenAI API-backed through `OPENAI_API_KEY` and the Responses API.

That design cannot use ChatGPT subscription-backed Codex authentication. Even after fixing OpenAI transport bugs, a fixture demo can still fail because API billing/quota is separate from ChatGPT subscription billing.

The product requirement is now:
- keep the deterministic evidence layer unchanged
- preserve provider-agnostic issue planner and claim composer contracts
- add a runtime path that can use local `codex login` credentials without requiring `OPENAI_API_KEY`

## Observed Runtime Reality

Local validation on this machine shows:
- `codex login status` returns `Logged in using ChatGPT`
- `codex exec --json --output-last-message ... "Reply with exactly: []"` succeeds under the current local ChatGPT-backed login state

That makes `codex exec` the viable local runtime boundary for subscription-backed synthesis.

## Options Considered

### 1. Keep only the OpenAI API provider

Pros:
- simplest code path
- no new transport abstraction

Cons:
- does not solve the subscription-backed runtime requirement
- keeps demos blocked on API quota and project billing

Rejected.

### 2. Add a `codex-oauth` provider backed by `codex exec`

Pros:
- matches the locally available subscription-backed auth path
- keeps provider logic outside the deterministic evidence layer
- can preserve the same issue planner / claim composer JSON contracts

Cons:
- introduces a CLI transport boundary
- requires careful output parsing, timeout handling, and auth checks

Chosen.

### 3. Replace the provider layer with a Codex-only transport

Pros:
- smallest mental model once migrated

Cons:
- would regress provider-agnostic design
- would throw away the OpenAI API path that is still useful for project-key deployments

Rejected.

## Chosen Design

Keep the current provider-agnostic model contracts:
- `IssuePlannerProvider`
- `ClaimComposerProvider`

Add a second runtime family:
- `openai`: API key + Responses API
- `codex-oauth`: local `codex exec` + ChatGPT/Codex login

The deterministic evidence layer, validator, critic, renderer, and decision record layers do not change their contracts.

## Runtime Boundary

### Shared invariant

Every provider runtime must:
- consume the same typed internal payloads
- return schema-valid JSON only
- preserve bounded inputs from the evidence layer
- surface transport/auth failures explicitly

### `codex-oauth` transport

The `codex-oauth` provider will:
- verify local Codex auth before running
- invoke `codex exec` non-interactively
- pass a strict prompt that asks for JSON only
- parse the final message or structured output file
- hand the parsed JSON to the existing issue planner / claim composer validation logic

It must not:
- read or copy auth tokens into repo files
- bypass validator/citation enforcement
- change the issue-map or claim-object schema

## Provider Selection

Runner scripts should move from ad hoc `if provider == "openai"` wiring to an explicit provider registry.

Target modes:
- `deterministic`
- `openai`
- `codex-oauth`

Provider selection rules:
- `deterministic` requires no external auth
- `openai` requires API credentials
- `codex-oauth` requires successful local `codex login status`

Provider-specific failure messages should be immediate and explicit.

## Security and Credential Handling

The repo must treat Codex auth as local machine state, not project configuration.

Rules:
- never persist OAuth tokens in repo files or artifacts
- never mirror Codex auth into `.env`
- decision records and runtime artifacts may record provider name and transport errors, but not secrets

## Failure Handling

`codex-oauth` failures should classify as:
- auth missing
- CLI unavailable
- timeout
- malformed JSON
- provider execution failure

Retry policy:
- no retry for auth-missing or CLI-missing failures
- one retry for timeout or malformed-JSON failures, matching existing model-layer policy

## Testing Strategy

Required coverage:
- provider auth check behavior
- command payload construction
- JSON output parsing
- malformed output rejection
- script/provider selection wiring
- one end-to-end fixture run using a fake Codex transport

Live subscription-backed demo runs remain optional verification, not unit-test requirements.

## Out of Scope

This redesign does not:
- change issue-planner or claim-composer schemas
- relax citation rules
- replace the OpenAI API provider
- make the live evidence layer depend on Codex

## Delivery Sequence

1. Merge redesign docs and product-file updates.
2. Create a planning issue/PR for implementation breakdown.
3. Split child implementation issues for:
   - provider registry and CLI wiring
   - Codex runtime adapter
   - tests and README/runtime docs
4. Implement and merge child issues.
