# Backend Development Guidelines

> Repo-specific backend guidance for the current Python codebase.

---

## Overview

Backend work in this repo currently means:
- Python modules under `apps/agent/`
- mirrored unit tests under `tests/agent/`
- modelling/schema artifacts under `artifacts/modelling/`
- validation scripts under `scripts/`

Read this index first, then the relevant detailed docs.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Where Python runtime, tests, scripts, and modelling docs live | Active |
| [Type Safety](./type-safety.md) | Typing, dataclasses, enums, and contract boundaries | Active |
| [Database Guidelines](./database-guidelines.md) | Current modelling-first persistence rules | Active |
| [Error Handling](./error-handling.md) | How code raises errors vs returns typed failure states | Active |
| [Logging Guidelines](./logging-guidelines.md) | Current low-noise logging approach | Active |
| [Quality Guidelines](./quality-guidelines.md) | Verification commands, testing rules, and forbidden patterns | Active |

---

## Pre-Development Checklist

- Read `AGENTS.md` and `CLAUDE.md`
- Read this file
- Read the specific backend docs that match the task
- For cross-layer changes, also read `../guides/pre-implementation-checklist.md`

---

## Current Examples

- Runtime orchestration: `apps/agent/orchestrator.py`
- Typed pipeline contracts: `apps/agent/pipeline/types.py`
- Budget guard logic: `apps/agent/runtime/budget_guard.py`
- Ingestion normalization: `apps/agent/ingest/normalize.py`
- Runtime tests: `tests/agent/test_orchestrator.py`
- Validation scripts: `scripts/validate_artifacts.py`
