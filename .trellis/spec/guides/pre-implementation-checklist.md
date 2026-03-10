# Pre-Implementation Checklist

> Use this before changing shared contracts, workflow tooling, or cross-layer behavior.

---

## Checklist

- [ ] Which files define the current contract: runtime code, modelling docs, scripts, tests, or all of them?
- [ ] Is there already a spec entry in `.trellis/spec/` that should be updated first?
- [ ] Are there enums, dataclasses, dict keys, or fixture fields that must stay aligned?
- [ ] Will CI validators need updates too?
- [ ] Will this change affect session/worktree tooling or Trellis workflow assumptions?
- [ ] Should this change be documented as backend guidance or as a thinking guide?

---

## Typical Search Pass

```bash
rg -n "value_to_change|RunStatus|run_type|field_name" apps tests scripts artifacts .trellis
```

If you find the same concept in code, tests, modelling docs, and Trellis docs, treat it as a coordinated change instead of a single-file edit.
