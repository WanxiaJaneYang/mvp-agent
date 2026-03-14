# Modelling TODO (Prophet-Inspired, Project-Scoped)

Last updated: 2026-03-13

## Priority Queue

- [ ] P0: Define Codex OAuth runtime adapter contract for daily brief providers
  - Acceptance: auth discovery, command boundary, output parsing, and failure modes documented for `codex-oauth`.

- [ ] P0: Define provider selection and registry contract for daily brief runner scripts
  - Acceptance: one spec covers `deterministic`, `openai`, and `codex-oauth` selection plus provider-specific config validation.

- [x] P0: Record the daily-brief integrity execution order across the then-open issues
  - Acceptance: the repo docs point to `#135 -> #128 -> #129 -> #130 -> #131 -> #138 -> #134 -> #132 -> #133 -> #136 -> #69 -> #137 -> #74` and now preserve it as historical reference material rather than active backlog sequencing.

- [x] P0: Define `decision_record` artifact schema and storage location
  - Acceptance: markdown spec + JSON example + field-level validation rules.

- [x] P0: Wire `decision_record` generation into synthesis pipeline output
  - Acceptance: stage contract updated and one fixture demonstrating persisted output.

- [ ] P1: Add validated-synthesis memory retrieval design
  - Acceptance: retrieval flow doc with ingest criteria (approved-only) and ranking fields.

- [ ] P1: Add role-lane orchestration spec (research/risk/editorial/reviewer)
  - Acceptance: phase prompts, inputs/outputs, and failover behavior documented.

- [ ] P1: Define issue planner contract and prompt interface
  - Acceptance: issue map schema, provider interface, retry policy, and evaluation criteria documented.

- [ ] P1: Define claim composer contract and prompt interface
  - Acceptance: claim object schema, grounding rules, delta fields, and evaluation criteria documented.

- [ ] P1: Extend validator gates for deterministic fail/abstain behavior
  - Acceptance: explicit gate matrix for citation, paywall, diversity, and budget constraints.

- [ ] P2: Define fixed output templates (daily brief, event-risk brief, portfolio delta)
  - Acceptance: issue-centered template examples with required sections, visible evidence blocks, and max-length constraints.

- [ ] P2: Define reliability metrics and weekly review report format
  - Acceptance: metric definitions, SQL/source mapping, and reporting cadence.

## Notes

- Keep all work aligned with PRD v1.2 constraints: local-first, citation-grounded, issue-centered, no trading instructions.
- Do not relax paywall, budget hard-stop, or evidence requirements.
- Treat alert delivery as post-daily-brief scope until the daily-brief path is stable.
- Treat retrieval expansion as follow-on work after the daily-brief stabilization stream lands.
- Use `docs/status-matrix.md` as the canonical modelled/coded/verified status view.
