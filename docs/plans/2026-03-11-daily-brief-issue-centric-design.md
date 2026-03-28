# Daily Brief Issue-Centric Literature Review Design

## Goal

Redesign the deterministic daily-brief slice so the report reads like a short literature review across 2-3 important issues, instead of a flat set of global `prevailing` / `counter` / `minority` buckets that may discuss unrelated topics.

## Scope

This slice covers:
- replacing the current flat synthesis shape with issue-centered review blocks
- making `prevailing`, `counter`, and `minority` arguments belong to the same issue
- exposing exact supporting evidence directly under each argument
- updating validation, artifact persistence, and HTML rendering to match the new structure

This slice does not cover:
- live network fetch or broader retrieval changes
- model-generated prose
- email delivery redesign
- cross-run comparison logic

## Why This Change

The current vertical slice produces a structurally valid report, but it does not behave like a literature review. Each top-level section can draw from a different topic, which breaks the intended meaning of `prevailing`, `counter`, and `minority`.

The target reading experience is:
- 2-3 important issues for the day
- each issue framed as a focused question or thesis
- competing arguments nested inside that issue
- visible evidence so the reader can inspect exactly what supports each view

## Approaches Considered

### Option A: Keep the flat top-level section model and improve evidence selection

This would keep:
- top-level `prevailing`
- top-level `counter`
- top-level `minority`
- top-level `watch`

Why this is not preferred:
- the report still reads like unrelated buckets
- it cannot guarantee that competing arguments discuss one issue
- it does not match the desired literature-review shape

### Option B: Make issues the primary output unit

Add a top-level `issues` list where each issue contains:
- issue title or question
- summary paragraph
- nested `prevailing`, `counter`, and `minority` arguments
- visible evidence entries under each argument
- issue-specific `watch` items

Why this is preferred:
- matches the intended essay-like reading experience
- preserves deterministic structure for validation and rendering
- scales naturally from one issue to 2-3 issues
- keeps evidence and argument tightly bound

### Option C: Render a free-form essay and infer structure later

Why this is not preferred:
- weakens deterministic validation
- makes artifact persistence harder to inspect
- increases rewrite risk when the real runtime becomes more capable

## Selected Design

### Primary Output Shape

The daily brief becomes a list of issue-centered review blocks:

```json
{
  "issues": [
    {
      "issue_id": "issue_001",
      "title": "Will oil prices keep rising over the next few weeks?",
      "summary": "Short synthesis paragraph describing the debate.",
      "prevailing": [
        {
          "text": "Supply risks and recent price momentum support the dominant short-term bullish view.",
          "citation_ids": ["cite_001", "cite_002"],
          "confidence_label": "high",
          "evidence": [
            {
              "citation_id": "cite_001",
              "publisher": "Reuters",
              "published_at": "2026-03-11T08:00:00Z",
              "support_text": "Visible quote or snippet"
            }
          ]
        }
      ],
      "counter": [
        {
          "text": "Some reports argue prices may stabilize soon as demand expectations soften.",
          "citation_ids": ["cite_003"],
          "confidence_label": "medium",
          "evidence": []
        }
      ],
      "minority": [
        {
          "text": "A smaller camp expects longer-term upside with limited near-term acceleration.",
          "citation_ids": ["cite_004"],
          "confidence_label": "medium",
          "evidence": []
        }
      ],
      "watch": [
        {
          "text": "Watch the next inventory release and any OPEC guidance revisions.",
          "citation_ids": ["cite_005"]
        }
      ]
    }
  ]
}
```

The existing flat section shape should no longer be the primary synthesis contract for the daily brief path.

### Issue Count and Selection

- Select 2-3 issues per run when evidence supports them.
- Prefer issues with the strongest combined evidence and the clearest internal debate.
- If evidence only supports one issue, one issue is acceptable.
- If evidence does not support any issue-centered review, the run should continue through the existing abstain path.

### Issue Definition

An issue is a single market or macro question that can plausibly support:
- a dominant view
- a meaningful counter-view
- an optional minority or nuanced view

Examples:
- near-term oil-price direction
- whether slowing growth will change policy expectations
- whether labor-market cooling is materially changing the macro outlook

What does not qualify:
- three unrelated headlines collected into one issue
- arguments that share keywords but not a real common question

### Argument Rules

Within each issue:
- `prevailing`, `counter`, and `minority` must all address the same issue title/question
- the three argument groups may differ in strength, but they must remain comparable viewpoints
- `minority` can be explicit insufficient-evidence language if no credible minority view exists

Each argument entry should:
- state the claim in concise prose
- carry citation IDs
- expose visible evidence entries below the claim

### Evidence Presentation

The report must show exact support for each argument, not just a references list at the end.

For each evidence entry, display:
- publisher
- article or release title
- published date
- a visible quote/snippet
- link target via the citation reference

Paywall handling remains unchanged:
- `metadata_only` sources may show headline/snippet support
- they must not expose fabricated or extracted full-text quotes

### Summary Paragraph

Each issue includes a short synthesis paragraph that:
- frames the state of the debate
- describes where the balance of evidence sits
- does not introduce uncited new facts beyond what the argument blocks already support

The summary is a synthesis convenience layer, not a separate unsupported claim surface.

### Validation Impact

Stage-8 validation should move from validating only top-level sections to validating nested issue arguments.

Validation expectations:
- every issue argument bullet still has valid citation coverage
- core issue sections should be treated as:
  - `prevailing`
  - `counter`
  - `minority`
  - `watch`
- retry or abstain rules should operate on issue completeness rather than the old single global section set

The validator may normalize issue-centered data into its existing internal section logic, but the daily-brief contract exposed to renderer and artifacts should remain issue-centered.

### Artifact Contract Changes

The runtime artifact set should preserve inspectability under the new contract.

In addition to existing artifacts:
- `synthesis.json` should store the issue-centered structure
- `synthesis_bullets.json` should add issue identifiers and section names
- `bullet_citations.json` should add issue identifiers and section names
- `run_summary.json` should record how many issues were generated

If helpful for debugging, a dedicated `issue_map.json` artifact may also be written.

### HTML Rendering

The local HTML brief should render as a small literature-review page:
- top-level report header
- 2-3 issue sections
- issue title/question
- summary paragraph
- nested `Prevailing`, `Counter`, `Minority`, and `What to Watch`
- visible evidence list beneath each argument
- reference links that still resolve to the citations list

This should read like a compact essay with supporting notes, not a flat dashboard.

### Decision Record Impact

The decision record should continue to persist the final synthesis output, but downstream code must tolerate the issue-centered shape.

If any persistence helper assumes only flat top-level section keys, that helper must be generalized so section metadata includes issue context.

## Error Handling

- If evidence cannot be grouped into 2-3 coherent issues, fall back to the strongest issue count actually supported.
- If a given issue loses one or more unsupported arguments during validation, keep the issue only if it still reads coherently.
- If validation removes enough arguments that an issue no longer has a credible debate shape, drop the issue or route to abstain depending on remaining issue count.
- If no coherent issue remains after validation, use the explicit abstain flow.

## Testing Strategy

Tests should cover:
- grouping evidence into 2-3 issue-centered review blocks
- keeping `prevailing`, `counter`, and `minority` on one issue
- visible evidence extraction for each argument
- nested validation behavior
- HTML rendering of issue-centered sections and evidence lists
- abstain behavior when issue grouping is not possible

## Migration Notes

- This is a contract change, not a cosmetic rename.
- Flat top-level section consumers in the current daily-brief path must be updated together.
- The initial implementation should stay deterministic and rule-based.
- The design keeps open the possibility of richer model-written literature reviews later, but the first implementation should remain offline-friendly and testable.
