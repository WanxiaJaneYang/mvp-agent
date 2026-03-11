<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

Use the Trellis workflow in `@/.trellis/workflow.md` when starting a new session to:
- Initialize your developer identity
- Understand current project context
- Read relevant guidelines

Use `@/.trellis/` to learn:
- Development workflow (`workflow.md`)
- Project structure guidelines (`spec/`)
- Developer workspace (`workspace/`)

Keep this managed block so 'trellis update' can refresh the instructions.

<!-- TRELLIS:END -->

# AGENTS.md

## Agent Policy

### Core workflow
Use `explore -> plan -> code -> verify -> commit` for implementation tasks.

### Delivery workflow
Use `issue -> PR -> merge` as the default delivery path for all finalized work.
This applies to design changes, planning documents, implementation work, and bug fixes.

For redesign-heavy work, use the staged delivery chain:
`redesign issue -> redesign PR -> merge -> planning issue/PR -> merge -> child issues -> implementation PRs -> merge`.

When a redesign expands into multiple execution tracks, do not jump straight from redesign into local implementation.
First land planning, then split the work into child issues, then execute implementation through an agent team aligned to those child issues.

### Operating standards
1. Inspect repository state first (`git status`, current branch, pending local changes).
2. Keep changes minimal and aligned with existing architecture and conventions.
3. Run relevant validation for touched areas.
4. Update docs when behavior, commands, or workflow changes.
5. Summarize what changed, what was validated, and any residual risk.
6. When a step is finalized, make sure it is tracked through an issue first, then committed into a PR (or the active PR), and merged instead of leaving completed local-only work unpushed.
7. After redesign is merged, create a planning step before implementation starts; if the plan yields multiple workstreams, create child issues before coding.
8. For independent tasks that are unlikely to conflict, use separate branches and separate MRs instead of combining them in one MR.
9. For multi-stream implementation, prefer an agent team working against child issues instead of one undifferentiated branch of work.

### Repo-specific non-negotiables
1. No uncited factual claims in generated analysis outputs.
2. Respect local-first design and paywall policies from project artifacts.
3. Enforce budget and safety guardrails; stop on configured hard limits.
4. Minimize context bloat by reading only files needed for the current step.

### Policy references
- MR policy and approval workflow: `.codex/mr-flow-and-approvals.md`
- Reusable local skills: `.codex/skills/`, `.agents/skills/`

