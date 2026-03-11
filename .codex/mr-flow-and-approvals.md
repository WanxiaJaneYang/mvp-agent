# MR Flow And Approval Preferences

## User Preferences
- Default workflow is always: `issue -> PR -> merge`.
- This rule applies to design changes, planning docs, implementation work, and bug fixes.
- Do not repeatedly ask for GitHub-related approvals when an approved command prefix already exists.
- Prefer reusing saved approved prefixes for `gh`/GitHub operations.
- Batch GitHub operations to minimize approval prompts.
- If all comments are addressed and all CI checks pass, proceed to merge.
- If approval is required and self-approval is blocked, use admin merge when explicitly requested by user workflow.

## Standard MR Flow
1. Confirm there is a tracking issue for the work; if not, create one before treating the task as in-flight.
2. Identify the latest/open PR tied to the current branch; if none exists, create one.
3. Check CI status and review state.
4. Pull unresolved review threads/comments.
5. Address unaddressed comments in code/docs/workflows.
6. Resolve addressed threads.
7. Re-request review and re-check CI.
8. Iterate steps 4-7 until review threads are resolved and checks pass.
9. Merge PR (prefer normal merge; use `--admin` only when required by policy/workflow).
10. Verify merged state and report merge commit SHA.

## Operational Rules For Future Sessions
- Read this file at the start of MR-related tasks.
- Treat work without an issue or PR as not yet in the required delivery flow.
- Assume user wants end-to-end completion (fix -> resolve -> review -> merge) unless user says otherwise.
- Surface only hard blockers (policy limitations, failed CI, missing required reviewer approval).
- Keep user updates brief and action-focused.

## Agent Direction For This Repo
- Prefer repo-local skill prompts under `.agents/skills/` or `.codex/skills/` when they match the task.
- Before MR actions, check this file first for approval and flow preferences.

## Platform Constraints
- GitHub does not allow approving your own PR.
- If branch protection requires approval and no other approver is available, use admin merge only when user workflow explicitly allows it.

