from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Mapping


SECTION_TITLES = {
    "prevailing": "Prevailing",
    "counter": "Counter",
    "minority": "Minority",
    "watch": "Watch",
}


def render_daily_brief_html(
    *,
    output_path: Path,
    report_date: str,
    run_id: str,
    synthesis: Mapping[str, list[Mapping[str, Any]]],
    citation_store: Mapping[str, Mapping[str, Any]],
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    abstained = _is_abstained(synthesis)
    status_title = "Abstained" if abstained else "Validated"

    sections_html: list[str] = []
    for section, title in SECTION_TITLES.items():
        bullets = synthesis.get(section, [])
        bullet_items = "".join(_render_bullet(bullet) for bullet in bullets)
        sections_html.append(f"<section><h2>{escape(title)}</h2><ul>{bullet_items}</ul></section>")

    citations_html = "".join(
        _render_citation(citation_id=citation_id, citation=citation_store[citation_id])
        for citation_id in citation_store
    )

    html = (
        "<html><head><meta charset=\"utf-8\"><title>Daily Brief</title></head><body>"
        f"<header><h1>Daily Brief</h1><p>Date: {escape(report_date)}</p><p>Run: {escape(run_id)}</p>"
        f"<p>Status: {escape(status_title)}</p></header>"
        f"{''.join(sections_html)}"
        f"<section><h2>Citations</h2><ol>{citations_html}</ol></section>"
        "</body></html>"
    )
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _render_bullet(bullet: Mapping[str, Any]) -> str:
    citation_ids = [str(citation_id) for citation_id in bullet.get("citation_ids", [])]
    citation_text = ""
    if citation_ids:
        citation_text = " [" + ", ".join(escape(citation_id) for citation_id in citation_ids) + "]"
    return f"<li>{escape(str(bullet.get('text', '')))}{citation_text}</li>"


def _render_citation(*, citation_id: str, citation: Mapping[str, Any]) -> str:
    title = escape(str(citation.get("title") or citation_id))
    url = escape(str(citation.get("url") or ""))
    return f"<li id=\"{escape(citation_id)}\"><a href=\"{url}\">{title}</a></li>"


def _is_abstained(synthesis: Mapping[str, list[Mapping[str, Any]]]) -> bool:
    bullets: list[Mapping[str, Any]] = []
    for section_bullets in synthesis.values():
        if not isinstance(section_bullets, list):
            continue
        bullets.extend(bullet for bullet in section_bullets if isinstance(bullet, Mapping))
    if not bullets:
        return True
    return all("Insufficient evidence" in str(bullet.get("text", "")) for bullet in bullets)
