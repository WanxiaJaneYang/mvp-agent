# Post-Open-Issue Triage Plan

**Date:** 2026-03-14

## Scope and Evidence
- Baseline branch/worktree: `sync/origin-master-631bbc6` at `origin/master` commit `631bbc6`
- Recently landed stream: PRs `#143`-`#157`
- GitHub issue hygiene result on 2026-03-14: issues `#69`, `#74`, and `#128`-`#138` were closed with explicit PR and merge-commit references; `gh issue list --state open --limit 50` then returned no open issues
- Repo truth sources reviewed:
  - `docs/status-matrix.md`
  - `artifacts/modelling/backlog.json`
  - `artifacts/modelling/TODO.md`
  - `README.md`

## Completed Areas
- The major runtime areas in `docs/status-matrix.md` are all `modelled=yes`, `coded=yes`, `verified=yes`
- `artifacts/modelling/backlog.json` marks `M001` through `M010` as `implemented`
- The historical daily-brief integrity execution stream is now a completed program, not the active backlog

## What Is Still Unfinished
The remaining unchecked items in `artifacts/modelling/TODO.md` are now primarily modelling/specification debt rather than missing landed runtime work:

1. Provider/runtime contract documentation
   - Codex OAuth runtime adapter contract
   - Provider selection and registry contract
2. Daily-brief modelling contract debt
   - validated-synthesis memory retrieval design
   - role-lane orchestration spec
   - issue planner contract and prompt interface
   - claim composer contract and prompt interface
   - validator gate matrix for deterministic fail/abstain behavior
3. Output/reporting documentation debt
   - fixed output templates
   - reliability metrics and weekly review format

## Local Cleanup Debt
- The main workspace at `D:\aiProjects\workspaces\mvp-agent` remains dirty and is out of scope for this batch
- Multiple legacy worktrees and local branches remain registered under `.worktrees\`, including attached branches for already-landed streams
- Do not delete attached worktrees or local branches in the next batch until each candidate is checked for:
  - containment in current `origin/master`
  - no uncommitted local changes
  - no dependency on the dirty main workspace

## Recommended Next Workstreams
1. Open a new planning issue for provider/runtime contract reconciliation and land a docs/spec PR for the remaining P0 TODO items
2. Open a separate planning issue for the remaining P1 daily-brief modelling contract debt
3. Land a small follow-up docs/spec PR for P2 output-template and reliability-reporting definitions
4. Run a dedicated local-cleanup pass only after the dirty main workspace is isolated or cleaned

## Suggested Issue Creation Rules
- Do not reopen or clone issues `#69`, `#74`, or `#128`-`#138`
- Create new issues only when the gap is still visible in the current repo state
- Each new issue should cite the current repo evidence directly (`TODO.md`, `status-matrix.md`, `backlog.json`, or missing contract file coverage)
- Split independent work into separate issues and separate branches/MRs

## Stop Gate
- Do not resume implementation from the old execution-order list
- Do not start a new feature MR until the next batch has fresh tracking issues tied to current repo truth
- Treat this document as the handoff plan for the next real MR batch
