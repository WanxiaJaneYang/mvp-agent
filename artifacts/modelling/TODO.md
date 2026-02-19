# Modelling TODO (Prophet-Inspired, Project-Scoped)

Last updated: 2026-02-19

## Priority Queue

- [ ] P0: Define `decision_record` artifact schema and storage location
  - Acceptance: markdown spec + JSON example + field-level validation rules.

- [ ] P0: Wire `decision_record` generation into synthesis pipeline output
  - Acceptance: stage contract updated and one fixture demonstrating persisted output.

- [ ] P1: Add validated-synthesis memory retrieval design
  - Acceptance: retrieval flow doc with ingest criteria (approved-only) and ranking fields.

- [ ] P1: Add role-lane orchestration spec (research/risk/editorial/reviewer)
  - Acceptance: phase prompts, inputs/outputs, and failover behavior documented.

- [ ] P1: Extend validator gates for deterministic fail/abstain behavior
  - Acceptance: explicit gate matrix for citation, paywall, diversity, and budget constraints.

- [ ] P2: Define fixed output templates (daily brief, event-risk brief, portfolio delta)
  - Acceptance: template examples with required sections and max-length constraints.

- [ ] P2: Define reliability metrics and weekly review report format
  - Acceptance: metric definitions, SQL/source mapping, and reporting cadence.

## Notes

- Keep all work aligned with PRD v1.1 constraints: local-first, citation-grounded, no trading instructions.
- Do not relax paywall, budget hard-stop, or evidence requirements.
