from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Mapping


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
    citation_store: Mapping[str, Mapping[str, Any]],
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    issues = synthesis.get("issues", [])
    abstained = _is_abstained(synthesis)
    status_title = "Abstained" if abstained else "Validated"

    issues_html = "".join(_render_issue(issue) for issue in issues if isinstance(issue, Mapping))
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
      color-scheme: light;
      --bg: #f5f1e8;
      --paper: #fffdf8;
      --ink: #1f1a17;
      --muted: #6f645b;
      --line: #d8cec0;
      --accent: #9b4d2f;
    }}
    body {{
      margin: 0;
      padding: 32px 20px 48px;
      background: linear-gradient(180deg, #efe7d8 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }}
    main {{
      max-width: 960px;
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
      font-weight: 600;
      line-height: 1.2;
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
    .issues {{
      padding: 12px 32px 8px;
    }}
    .issue {{
      padding: 24px 0 28px;
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
    .argument ul,
    .references ol {{
      margin: 8px 0 0;
      padding-left: 20px;
    }}
    .argument li,
    .references li {{
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
    .references {{
      padding: 0 32px 28px;
      border-top: 1px solid var(--line);
    }}
    a {{
      color: var(--accent);
    }}
    .citation-link {{
      text-decoration: none;
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
        <span>Status: {escape(status_title)}</span>
      </div>
    </header>
    <section class="issues">
      {issues_html}
    </section>
    <section class="references">
      <h2>Citations</h2>
      <ol>{citations_html}</ol>
    </section>
  </main>
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _render_issue(issue: Mapping[str, Any]) -> str:
    title = escape(str(issue.get("title", "Key issue")))
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
    items = []
    if isinstance(bullets, list):
        items = [_render_bullet(bullet) for bullet in bullets if isinstance(bullet, Mapping)]
    return (
        '<section class="argument">'
        f"<h3>{escape(title)}</h3>"
        f"<ul>{''.join(items)}</ul>"
        "</section>"
    )


def _render_bullet(bullet: Mapping[str, Any]) -> str:
    citation_ids = [str(citation_id) for citation_id in bullet.get("citation_ids", [])]
    citation_text = ""
    if citation_ids:
        anchors = "".join(
            f' <a class="citation-link" href="#{escape(citation_id)}">[{escape(citation_id)}]</a>'
            for citation_id in citation_ids
        )
        citation_text = anchors

    evidence_html = ""
    evidence_items = bullet.get("evidence", [])
    if isinstance(evidence_items, list) and evidence_items:
        evidence_html = "".join(_render_evidence(evidence) for evidence in evidence_items if isinstance(evidence, Mapping))
        evidence_html = f'<div class="evidence">{evidence_html}</div>'

    return (
        "<li>"
        f"{escape(str(bullet.get('text', '')))}{citation_text}"
        f"{evidence_html}"
        "</li>"
    )


def _render_evidence(evidence: Mapping[str, Any]) -> str:
    publisher = escape(str(evidence.get("publisher", "")))
    published_at = escape(str(evidence.get("published_at", "")))
    support_text = escape(str(evidence.get("support_text", "")))
    return (
        '<div class="evidence-item">'
        f'<div class="evidence-meta">{publisher} | {published_at}</div>'
        f"<p>{support_text}</p>"
        "</div>"
    )


def _render_citation(*, citation_id: str, citation: Mapping[str, Any]) -> str:
    title = escape(str(citation.get("title") or citation_id))
    url = escape(str(citation.get("url") or ""))
    return f'<li id="{escape(citation_id)}"><a href="{url}">{title}</a></li>'


def _is_abstained(synthesis: Mapping[str, Any]) -> bool:
    issues = synthesis.get("issues", [])
    if not isinstance(issues, list) or not issues:
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
