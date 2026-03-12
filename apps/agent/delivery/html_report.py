from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Mapping

from apps.agent.pipeline.types import CitationStoreEntry

SECTION_TITLES = {
    "prevailing": "Prevailing",
    "counter": "Counter",
    "minority": "Minority",
    "watch": "What to Watch",
}


def render_daily_brief_html(
    *,
    output_path: Path,
    report_date: str,
    run_id: str,
    synthesis: Mapping[str, Any],
    citation_store: Mapping[str, CitationStoreEntry],
    guardrail_checks: Mapping[str, Any] | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    abstained = _is_abstained(synthesis)
    brief = synthesis.get("brief", {}) if isinstance(synthesis.get("brief"), Mapping) else {}
    citation_status = str((guardrail_checks or {}).get("citation_status") or ("abstained" if abstained else "ok"))
    analytical_status = str((guardrail_checks or {}).get("analytical_status") or "pass")
    publish_decision = str((guardrail_checks or {}).get("publish_decision") or ("hold" if abstained else "publish"))
    issues = _normalized_issues(synthesis)
    overview_html = _render_overview(brief)

    issues_html = "".join(_render_issue(issue) for issue in issues if isinstance(issue, Mapping))
    changed_html = _render_changed_section(synthesis.get("changed"))
    guardrails_html = _render_guardrails(guardrail_checks)
    citations_html = "".join(
        _render_citation(citation_id=citation_id, citation=citation_store[citation_id])
        for citation_id in citation_store
    )

    html = f"""<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Daily Brief</title>
  <style>
    :root {{
      --bg: #efe8dc;
      --paper: #fffdf8;
      --ink: #1f1b18;
      --muted: #6e645a;
      --line: #d8ccbc;
      --accent: #9a4e2f;
    }}
    body {{
      margin: 0;
      padding: 32px 20px 48px;
      background: linear-gradient(180deg, #efe7d8 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      background: var(--paper);
      border: 1px solid var(--line);
      box-shadow: 0 18px 50px rgba(73, 54, 33, 0.08);
    }}
    header {{
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--line);
    }}
    h1, h2, h3 {{
      margin: 0;
      line-height: 1.2;
      font-weight: 600;
    }}
    h1 {{
      font-size: 2.1rem;
      margin-bottom: 12px;
    }}
    h2 {{
      font-size: 1.4rem;
      margin-bottom: 10px;
    }}
    h3 {{
      font-size: 0.95rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 8px;
    }}
    p {{
      margin: 0 0 12px;
      line-height: 1.65;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .issues, .changed, .guardrails, .references {{
      padding: 20px 32px 8px;
    }}
    .issue {{
      padding: 10px 0 28px;
      border-bottom: 1px solid var(--line);
    }}
    .issue:last-child {{
      border-bottom: 0;
    }}
    .summary {{
      color: var(--muted);
      max-width: 72ch;
    }}
    .arguments {{
      display: grid;
      gap: 18px;
      margin-top: 18px;
    }}
    .argument {{
      border-left: 3px solid var(--line);
      padding-left: 14px;
    }}
    .argument ul, .references ol, .changed ul, .guardrails ul {{
      margin: 8px 0 0;
      padding-left: 20px;
    }}
    .argument li, .references li, .changed li, .guardrails li {{
      margin-bottom: 10px;
      line-height: 1.55;
    }}
    .evidence {{
      margin-top: 10px;
      padding: 10px 12px;
      background: #f8f3ea;
      border: 1px solid #e7dcc9;
    }}
    .evidence-meta {{
      color: var(--muted);
      font-size: 0.92rem;
      margin-bottom: 4px;
    }}
    .citation-link {{
      text-decoration: none;
      color: var(--accent);
      margin-left: 4px;
    }}
    a {{
      color: var(--accent);
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Daily Brief</h1>
      <div class="meta">
        <span>Date: {escape(report_date)}</span>
        <span>Run: {escape(run_id)}</span>
        <span>Citation status: {escape(_label(citation_status))}</span>
        <span>Analytical quality: {escape(_label(analytical_status))}</span>
        <span>Publish decision: {escape(_label(publish_decision))}</span>
      </div>
    </header>
    {overview_html}
    <section class="issues">
      <h2>Issues</h2>
      {issues_html}
    </section>
    {changed_html}
    {guardrails_html}
    <section class="references">
      <h2>Citations</h2>
      <ol>{citations_html}</ol>
    </section>
  </main>
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _render_overview(brief: Mapping[str, Any]) -> str:
    bottom_line = str(brief.get("bottom_line") or "").strip()
    takeaways = brief.get("top_takeaways")
    watchlist = brief.get("watchlist")
    if not bottom_line and not isinstance(takeaways, list) and not isinstance(watchlist, list):
        return ""

    takeaways_html = ""
    if isinstance(takeaways, list) and takeaways:
        items = "".join(f"<li>{escape(str(item))}</li>" for item in takeaways if str(item).strip())
        takeaways_html = f"<h2>Key Takeaways</h2><ul>{items}</ul>"

    watchlist_html = ""
    if isinstance(watchlist, list) and watchlist:
        items = "".join(f"<li>{escape(str(item))}</li>" for item in watchlist if str(item).strip())
        watchlist_html = f"<h2>Watchlist</h2><ul>{items}</ul>"

    return (
        '<section class="issues">'
        "<h2>Bottom Line</h2>"
        f"<p>{escape(bottom_line)}</p>"
        f"{takeaways_html}"
        f"{watchlist_html}"
        "</section>"
    )


def _render_issue(issue: Mapping[str, Any]) -> str:
    title = escape(str(issue.get("title") or issue.get("issue_question") or "Key issue"))
    summary = escape(str(issue.get("summary", "")))
    sections_html = "".join(
        _render_issue_section(title=title_text, bullets=issue.get(section, []))
        for section, title_text in SECTION_TITLES.items()
    )
    return (
        '<article class="issue">'
        f"<h2>{title}</h2>"
        f'<p class="summary">{summary}</p>'
        f'<div class="arguments">{sections_html}</div>'
        "</article>"
    )


def _render_issue_section(*, title: str, bullets: Any) -> str:
    bullet_items = ""
    if isinstance(bullets, list):
        bullet_items = "".join(_render_bullet(bullet) for bullet in bullets if isinstance(bullet, Mapping))
    return (
        '<section class="argument">'
        f"<h3>{escape(title)}</h3>"
        f"<ul>{bullet_items}</ul>"
        "</section>"
    )


def _render_bullet(bullet: Mapping[str, Any]) -> str:
    citation_ids = [str(citation_id) for citation_id in bullet.get("citation_ids", [])]
    citation_links = "".join(
        f' <a class="citation-link" href="#{escape(citation_id)}">[{escape(citation_id)}]</a>'
        for citation_id in citation_ids
    )
    novelty = str(bullet.get("novelty_vs_prior_brief") or bullet.get("delta_label") or "").strip()
    novelty_html = f' <strong>({escape(_label(novelty))})</strong>' if novelty and novelty != "unknown" else ""
    why_it_matters = str(bullet.get("why_it_matters") or "").strip()
    delta_explanation = str(bullet.get("delta_explanation") or "").strip()
    evidence_html = _render_evidence_block(bullet.get("evidence"))
    return (
        "<li>"
        f"{escape(str(bullet.get('text', '')))}{novelty_html}{citation_links}"
        f"{_render_callout('Why it matters', why_it_matters)}"
        f"{_render_callout('Delta', delta_explanation)}"
        f"{evidence_html}"
        "</li>"
    )


def _render_evidence_block(evidence_items: Any) -> str:
    if not isinstance(evidence_items, list) or not evidence_items:
        return ""
    evidence_html = "".join(
        _render_evidence_item(evidence)
        for evidence in evidence_items
        if isinstance(evidence, Mapping)
    )
    return f'<div class="evidence">{evidence_html}</div>'


def _render_evidence_item(evidence: Mapping[str, Any]) -> str:
    publisher = escape(str(evidence.get("publisher") or ""))
    published_at = escape(str(evidence.get("published_at") or ""))
    support_text = escape(str(evidence.get("support_text") or ""))
    return (
        '<div class="evidence-item">'
        f'<div class="evidence-meta">{publisher} | {published_at}</div>'
        f"<p>{support_text}</p>"
        "</div>"
    )


def _render_changed_section(changed_bullets: Any) -> str:
    if not isinstance(changed_bullets, list) or not changed_bullets:
        return ""
    items = "".join(_render_bullet(bullet) for bullet in changed_bullets if isinstance(bullet, Mapping))
    return (
        '<section class="changed">'
        "<h2>What Changed</h2>"
        f"<ul>{items}</ul>"
        "</section>"
    )


def _render_citation(*, citation_id: str, citation: Mapping[str, Any]) -> str:
    title = escape(str(citation.get("title") or citation_id))
    url = escape(str(citation.get("url") or ""))
    return f'<li id="{escape(citation_id)}"><a href="{url}">{title}</a></li>'


def _render_guardrails(guardrail_checks: Mapping[str, Any] | None) -> str:
    if guardrail_checks is None:
        return ""
    notes = "".join(
        f"<li>{escape(str(note))}</li>"
        for note in guardrail_checks.get("notes", [])
        if isinstance(note, str)
    )
    return (
        '<section class="guardrails">'
        "<h2>Guardrails</h2>"
        "<ul>"
        f"<li>Budget: {escape(_label(str(guardrail_checks.get('budget_check', 'warn'))))}</li>"
        f"<li>Diversity: {escape(_label(str(guardrail_checks.get('diversity_check', 'warn'))))}</li>"
        f"<li>Citations: {escape(_label(str(guardrail_checks.get('citation_check', 'warn'))))}</li>"
        f"<li>Analytical quality: {escape(_label(str(guardrail_checks.get('analytical_status', 'pass'))))}</li>"
        f"{notes}"
        "</ul>"
        "</section>"
    )


def _label(value: str) -> str:
    return value[:1].upper() + value[1:].lower()


def _render_callout(title: str, value: str) -> str:
    if not value:
        return ""
    return f'<p><strong>{escape(title)}:</strong> {escape(value)}</p>'


def _is_abstained(synthesis: Mapping[str, Any]) -> bool:
    issues = _normalized_issues(synthesis)
    if not issues:
        return True

    bullets: list[Mapping[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, Mapping):
            continue
        for section in SECTION_TITLES:
            section_bullets = issue.get(section, [])
            if not isinstance(section_bullets, list):
                continue
            bullets.extend(bullet for bullet in section_bullets if isinstance(bullet, Mapping))

    if not bullets:
        return True
    return all("Insufficient evidence" in str(bullet.get("text", "")) for bullet in bullets)


def _normalized_issues(synthesis: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    issues = synthesis.get("issues")
    if isinstance(issues, list):
        return [issue for issue in issues if isinstance(issue, Mapping)]

    has_flat_sections = any(isinstance(synthesis.get(section), list) for section in SECTION_TITLES)
    if not has_flat_sections:
        return []

    return [
        {
            "issue_id": "issue_001",
            "title": "Key issue",
            "issue_question": "Key issue",
            "summary": "",
            "prevailing": synthesis.get("prevailing", []),
            "counter": synthesis.get("counter", []),
            "minority": synthesis.get("minority", []),
            "watch": synthesis.get("watch", []),
        }
    ]
