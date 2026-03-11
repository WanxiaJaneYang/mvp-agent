# MR Flow And Approval Preferences

## User Preferences
- Default workflow is always: `issue -> PR -> merge`.
- This rule applies to design changes, planning docs, implementation work, and bug fixes.
- After redesign work, the required sequence is: `redesign -> planning -> child issues -> implementation`.
- Planning is not optional when a redesign changes architecture, contracts, or multi-step execution.
- When planning produces multiple implementation tracks, create child issues before implementation starts.
- Multi-stream implementation should be executed by an agent team aligned to child issues, not as one ad hoc undifferentiated task.
- Do not repeatedly ask for GitHub-related approvals when an approved command prefix already exists.
- Prefer reusing saved approved prefixes for `gh`/GitHub operations.
- Batch GitHub operations to minimize approval prompts.
- If all comments are addressed and all CI checks pass, proceed to merge.
- If approval is required and self-approval is blocked, use admin merge when explicitly requested by user workflow.

## Standard MR Flow
1. Confirm there is a tracking issue for the work; if not, create one before treating the task as in-flight.
2. If the current work is a redesign, land that redesign in its own PR before moving to planning.
3. After redesign merges, create the planning issue/PR and land planning before implementation begins.
4. If planning yields multiple execution tracks, create child issues and map implementation branches/PRs to them.
5. Identify the latest/open PR tied to the current branch; if none exists, create one.
6. Check CI status and review state.
7. Pull unresolved review threads/comments.
8. Address unaddressed comments in code/docs/workflows.
9. Resolve addressed threads.
10. Re-request review and re-check CI.
11. Iterate steps 7-10 until review threads are resolved and checks pass.
12. Merge PR (prefer normal merge; use `--admin` only when required by policy/workflow).
13. Verify merged state and report merge commit SHA.

## Operational Rules For Future Sessions
- Read this file at the start of MR-related tasks.
- Treat work without an issue or PR as not yet in the required delivery flow.
- Treat redesign without a follow-on planning step as incomplete delivery flow.
- Treat multi-stream implementation without child issues as incomplete delivery flow.
- Assume user wants end-to-end completion (fix -> resolve -> review -> merge) unless user says otherwise.
- Surface only hard blockers (policy limitations, failed CI, missing required reviewer approval).
- Keep user updates brief and action-focused.

## Agent Direction For This Repo
- Prefer repo-local skill prompts under `.agents/skills/` or `.codex/skills/` when they match the task.
- Before MR actions, check this file first for approval and flow preferences.

## Platform Constraints
- GitHub does not allow approving your own PR.
- If branch protection requires approval and no other approver is available, use admin merge only when user workflow explicitly allows it.

