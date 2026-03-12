# Brief Editorial Planner Design

## Problem Statement

The daily brief currently starts issue generation directly from the evidence pack.
That skips the editorial step where the runtime should first decide:

- the main thesis of the brief
- how many issues the day actually supports
- whether the brief should render in full or compressed mode
- which items belong in takeaways or the watchlist

Without that stage, the system starts writing issue cards before it has chosen the shape of the brief.

## Target Contract

Add a `BriefPlan` contract before `IssueMap` generation.

Required fields:

- `brief_id`
- `brief_thesis`
- `top_takeaways`
- `issue_budget`
- `render_mode`
- `source_scarcity_mode`
- `candidate_issue_seeds`
- `issue_order`
- `watchlist`
- `reason_codes`

## Runner Changes

The runner should expose an explicit planner stage:

1. build the evidence pack
2. summarize the evidence corpus
3. generate a `BriefPlan`
4. pass `BriefPlan` into issue planning

The first implementation can use a local planner provider and heuristic corpus summary.

## Rendering Changes

The renderer should expose the brief plan at the top of the report:

- `Bottom line`
- `Key takeaways`
- `Watchlist`

That is the minimum editorial layer required before the issue cards.

## Test Plan

- source-rich corpus -> `render_mode=full`, `issue_budget=2`
- source-scarce corpus -> `render_mode=compressed`, `issue_budget=1`
- issue planner input includes `brief_plan`
- rendered HTML shows `Bottom line` and `Key takeaways`
- runtime artifacts persist `brief_plan.json`
