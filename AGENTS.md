# AGENTS.md

## Agent Policy

### Core workflow
Use `explore -> plan -> code -> verify -> commit` for implementation tasks.

### Operating standards
1. Inspect repository state first (`git status`, current branch, pending local changes).
2. Keep changes minimal and aligned with existing architecture and conventions.
3. Run relevant validation for touched areas.
4. Update docs when behavior, commands, or workflow changes.
5. Summarize what changed, what was validated, and any residual risk.

### Repo-specific non-negotiables
1. No uncited factual claims in generated analysis outputs.
2. Respect local-first design and paywall policies from project artifacts.
3. Enforce budget and safety guardrails; stop on configured hard limits.
4. Minimize context bloat by reading only files needed for the current step.

### Policy references
- MR policy and approval workflow: `.codex/mr-flow-and-approvals.md`
- Reusable local skills: `.codex/skills/`, `.agents/skills/`

