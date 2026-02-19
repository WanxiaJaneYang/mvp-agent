# Incremental MCP Adoption Plan

**Date:** 2026-02-19  
**Status:** Proposed  
**Scope:** Local-first MVP assistant (no cloud migration required for initial rollout)

## 1) Why MCP for this project

Model Context Protocol (MCP) gives us a standard way to expose internal capabilities as tools/resources with explicit contracts, transport options, and server boundaries.  
For this project, the best near-term value is:

1. Cleaner tool boundaries for retrieval, validation, and budgeting.
2. Better observability and auditability of which tool produced which evidence.
3. Safer incremental extension as source ingestion and analysis features expand.

## 2) Constraints to preserve

1. No uncited factual claims.
2. Paywall-safe behavior (`metadata_only` remains strict).
3. Hard budget stop before expensive model/tool work.
4. Local-first execution and storage.
5. Deterministic retry/abstain behavior.

These constraints remain enforced by existing validators/runtime guards; MCP should wrap and expose these controls, not replace them.

## 3) Current architecture touchpoints

1. `apps/agent/validators/citation_validator.py`  
2. `apps/agent/pipeline/stage8_validation.py`  
3. `apps/agent/runtime/budget_guard.py`  
4. Modelling contracts in:
   - `artifacts/modelling/pipeline.md`
   - `artifacts/modelling/citation_contract.md`
   - `artifacts/modelling/data_model.md`

## 4) Incremental rollout phases

## Phase 0: Interface Design (docs + contracts only)

Goal: define stable MCP tool/resource contracts before runtime integration.

Deliverables:
1. `docs/plans/mcp-interface-contracts.md`:
   - tool names, input/output schemas, error codes, timeout budgets.
2. Mapping table from existing modules -> MCP tools.
3. Security policy for server permissions and allowed file/network operations.

Initial tool candidates:
1. `validate_synthesis_citations`
2. `evaluate_budget_guard`
3. `run_stage8_validation`
4. `get_source_registry_entry`
5. `get_citation_contract_rules`

Exit criteria:
1. Contracts reviewed and aligned with PRD + PROJECT_FACT constraints.
2. Every tool has explicit failure modes (`retry`, `abstain`, `hard-stop`).

## Phase 1: Local MCP Server (read-only + validation tools)

Goal: stand up a local MCP server that wraps existing deterministic modules first.

Deliverables:
1. `apps/agent/mcp/server.py` (or equivalent) with stdio transport.
2. Tool handlers for:
   - citation validation
   - stage-8 synthesis validation
   - budget guard checks
3. Unit tests for tool handlers and schema validation.

Exit criteria:
1. Existing tests still pass.
2. New MCP tool tests pass.
3. Same inputs produce same validation outcomes pre/post MCP wrapper.

## Phase 2: Retrieval + Policy Resources

Goal: expose modelling artifacts as MCP resources used by the runtime.

Deliverables:
1. MCP resources for:
   - source registry
   - citation contract
   - pipeline policy snippets
2. Versioned artifact access (resource includes source revision/hash).
3. Caching rules for local resource reads.

Exit criteria:
1. Runtime can consume these resources without bypassing existing policy checks.
2. Resource reads are traceable in run logs.

## Phase 3: Orchestrator Integration

Goal: route selected internal calls through MCP without broad refactor risk.

Deliverables:
1. Feature flag: `USE_MCP_VALIDATION=true/false`.
2. Adapter layer allowing fallback to direct local function calls.
3. Observability fields in run logs:
   - tool name
   - latency
   - input/output hash
   - failure reason

Exit criteria:
1. Canary runs show parity with direct-call mode.
2. No increase in policy violations or budget overruns.

## Phase 4: Hardening + CI Gates

Goal: make MCP path production-safe for this project scope.

Deliverables:
1. CI jobs:
   - MCP tool schema contract tests
   - parity tests (direct-call vs MCP-call)
   - timeout/retry behavior tests
2. Security controls:
   - minimal runtime permissions
   - explicit allowlist of exposed tools/resources
3. Runbook: failure handling and rollback to direct-call mode.

Exit criteria:
1. CI required checks include MCP contract/parity tests.
2. Rollback switch validated in test and documented.

## 5) Sequencing recommendation

Recommended order:
1. Phase 0
2. Phase 1
3. Phase 4 (minimum hardening subset for adopted tools)
4. Phase 2
5. Phase 3

Rationale: validate deterministic and safety-critical tools first, harden early, then expand surface area.

## 6) Key risks and mitigations

1. Risk: MCP adds complexity before behavior is stable.  
   Mitigation: start with wrappers over deterministic existing modules only.

2. Risk: policy drift between direct and MCP paths.  
   Mitigation: parity tests + feature-flag fallback.

3. Risk: larger attack surface from new tool endpoints.  
   Mitigation: minimal permissions, allowlist-only tools, local transport first.

4. Risk: non-deterministic failures from external dependencies.  
   Mitigation: pin versions, timeout budgets, explicit retry policy.

## 7) First implementation slice (next task)

Build a minimal local MCP server exposing only:
1. `evaluate_budget_guard`
2. `validate_synthesis_citations`
3. `run_stage8_validation`

Add parity tests against direct function calls and keep fallback path enabled by default.

## 8) Success metrics

1. 100% parity on validation outputs between direct and MCP modes.
2. No regression in citation/paywall/budget guard behavior.
3. Stable CI pass rate after MCP checks become required.
4. Reduced integration friction when adding new tool-capabilities.

## References

1. MCP official docs: https://modelcontextprotocol.io/docs/getting-started/intro  
2. MCP Python SDK (official): https://github.com/modelcontextprotocol/python-sdk  
3. MCP TypeScript SDK (official): https://github.com/modelcontextprotocol/typescript-sdk  
4. Anthropic MCP docs (overview + connectors): https://docs.anthropic.com/en/docs/claude-code/mcp  
