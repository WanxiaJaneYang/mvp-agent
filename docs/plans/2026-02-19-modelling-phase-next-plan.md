# Modelling Phase Next Steps Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolve modelling-spec drift and complete the remaining modelling artifacts (pipeline, alert scoring, backlog) needed to move into implementation.

**Architecture:** Keep the current documentation-first modelling workflow. Align budget and checklist source-of-truth first, then define execution pipeline, alert policy, and actionable implementation backlog with acceptance criteria that map directly to PRD and PROJECT_FACT constraints.

**Tech Stack:** Markdown documentation, JSON backlog artifacts, Git workflow

---

### Task 1: Fix modelling documentation drift

**Files:**
- Modify: `artifacts/modelling/MODELLING_CHECKLIST.md`
- Modify: `artifacts/PRD.md`
- Modify: `CLAUDE.md`

1. Mark completed modelling items accurately in checklist (at minimum item B).
2. Align hourly budget cap values to non-negotiable constraints (`PROJECT_FACT`).
3. Keep edits minimal and scoped to inconsistent lines.

### Task 2: Create missing modelling artifacts

**Files:**
- Create: `artifacts/modelling/pipeline.md`
- Create: `artifacts/modelling/alert_scoring.md`
- Create: `artifacts/modelling/backlog.json`

1. Define stage-by-stage daily pipeline with failure handling, retry logic, and hard-stop limits.
2. Define alert scoring formula, category rules, thresholds, cooldown, daily cap, and bundling behavior.
3. Define build backlog tickets with clear acceptance criteria tied to A-I checklist and PRD constraints.

### Task 3: Verify artifacts and record progress

**Files:**
- Modify: `claude-progress.txt`

1. Validate `backlog.json` parses as valid JSON.
2. Validate created files exist and checklist state reflects reality.
3. Add a new progress session with what changed, validation run, and next single step.
4. Commit with a single focused message.
