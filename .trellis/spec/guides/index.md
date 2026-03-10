# Thinking Guides

> Guides for what to check before changing contracts, shared values, or cross-layer flows.

---

## Available Guides

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| [Pre-Implementation Checklist](./pre-implementation-checklist.md) | Quick gate before changing contracts or workflows | Before editing |
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | Identify repeated patterns and sync risks | When similar values/logic appear in multiple places |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Think through data flow and ownership boundaries | When code, modelling docs, and tests interact |

---

## Repo Notes

In this repo, cross-layer work usually means some combination of:
- runtime code in `apps/agent/`
- modelling contracts in `artifacts/modelling/`
- validation scripts in `scripts/`
- regression coverage in `tests/agent/`

Start with the pre-implementation checklist when a change affects any of those boundaries.
