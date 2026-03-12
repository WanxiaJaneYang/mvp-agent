from __future__ import annotations

from html.parser import HTMLParser
from io import StringIO
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.request import Request, urlopen

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MVP-Agent/0.1; +https://example.test/local)",
    "Accept": (
        "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, "
        "text/html;q=0.8, application/pdf;q=0.8, */*;q=0.7"
    ),
}


def fetch_live_payloads_for_source(
    *,
    source: Mapping[str, Any],
    fetched_at_utc: str | None = None,
    timeout_seconds: int = 20,
) -> list[dict[str, Any]]:
    source_type = str(source["type"])
    if source_type not in {"rss", "html", "pdf"}:
        raise ValueError(f"Unsupported live fetch source type: {source_type}")
    request = Request(str(source["url"]), headers=DEFAULT_REQUEST_HEADERS)
    with urlopen(request, timeout=timeout_seconds) as response:
        response_bytes = response.read()

    resolved_fetched_at = fetched_at_utc or _utc_now_iso()
    if source_type == "rss":
        feed_text = response_bytes.decode("utf-8", errors="replace")
        return parse_rss_feed(feed_text=feed_text, fetched_at_utc=resolved_fetched_at)
    if source_type == "html":
        html_text = response_bytes.decode("utf-8", errors="replace")
        return [_html_payload_from_page(source=source, html_text=html_text, fetched_at_utc=resolved_fetched_at)]
    if source_type == "pdf":
        return [_pdf_payload_from_bytes(source=source, pdf_bytes=response_bytes, fetched_at_utc=resolved_fetched_at)]
    raise ValueError(f"Unsupported live fetch source type: {source_type}")


def parse_rss_feed(*, feed_text: str, fetched_at_utc: str) -> list[dict[str, Any]]:
    root = ET.fromstring(feed_text)
    items = root.findall(".//item")
    if items:
        return [_rss_item_to_payload(item=item, fetched_at_utc=fetched_at_utc) for item in items]

    entries = root.findall(".//{*}entry")
    if entries:
        return [
            _atom_entry_to_payload(entry=entry, fetched_at_utc=fetched_at_utc) for entry in entries
        ]

    return []


def _rss_item_to_payload(*, item: ET.Element, fetched_at_utc: str) -> dict[str, Any]:
    return {
        "url": _first_text(item, "link"),
        "title": _first_text(item, "title"),
        "author": _first_text(item, "author", "{*}creator"),
        "language": None,
        "published_at": _normalize_timestamp(
            _first_text(item, "pubDate", "{*}published", "{*}updated")
        ),
        "fetched_at": fetched_at_utc,
        "summary": _first_text(item, "description", "{*}summary"),
        "body_text": _first_text(item, "{*}encoded", "{*}content"),
        "doc_type": "rss",
    }


def _atom_entry_to_payload(*, entry: ET.Element, fetched_at_utc: str) -> dict[str, Any]:
    link = entry.find("{*}link")
    href = link.get("href") if link is not None else None
    return {
        "url": href,
        "title": _first_text(entry, "{*}title"),
        "author": _first_text(entry, "{*}author/{*}name", "{*}author"),
        "language": None,
        "published_at": _normalize_timestamp(_first_text(entry, "{*}published", "{*}updated")),
        "fetched_at": fetched_at_utc,
        "summary": _first_text(entry, "{*}summary"),
        "body_text": _first_text(entry, "{*}content"),
        "doc_type": "rss",
    }


def _html_payload_from_page(
    *,
    source: Mapping[str, Any],
    html_text: str,
    fetched_at_utc: str,
) -> dict[str, Any]:
    parser = _HtmlPayloadParser()
    parser.feed(html_text)
    parser.close()
    canonical_url = parser.canonical_url or str(source["url"])
    return {
        "canonical_url": canonical_url,
        "headline": parser.title,
        "byline": parser.author,
        "language": parser.language,
        "published_at": _normalize_timestamp(parser.published_at),
        "fetched_at": fetched_at_utc,
        "snippet": parser.description,
        "text": parser.body_text,
        "doc_type": "html",
    }


def _pdf_payload_from_bytes(
    *,
    source: Mapping[str, Any],
    pdf_bytes: bytes,
    fetched_at_utc: str,
) -> dict[str, Any]:
    url = str(source["url"])
    return {
        "url": url,
        "canonical_url": url,
        "title": source.get("name"),
        "author": None,
        "language": None,
        "published_at": None,
        "fetched_at": fetched_at_utc,
        "summary": None,
        "pdf_bytes": pdf_bytes,
        "doc_type": "pdf",
    }


def _first_text(element: ET.Element, *paths: str) -> str | None:
    for path in paths:
        child = element.find(path)
        if child is not None and child.text:
            return child.text.strip()
    return None


def _normalize_timestamp(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, IndexError):
        pass
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except ValueError:
        return value


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class _HtmlPayloadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.author: str | None = None
        self.description: str | None = None
        self.published_at: str | None = None
        self.canonical_url: str | None = None
        self.language: str | None = None
        self.body_text: str | None = None
        self._current_tag: str | None = None
        self._title_buffer = StringIO()
        self._body_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): value for name, value in attrs}
        if tag == "html":
            self.language = attributes.get("lang")
        elif tag == "title":
            self._current_tag = "title"
        elif tag == "body":
            self._body_depth += 1
        elif tag == "meta":
            self._capture_meta(attributes)
        elif tag == "link" and attributes.get("rel", "").lower() == "canonical":
            self.canonical_url = attributes.get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            title = self._title_buffer.getvalue().strip()
            if title:
                self.title = title
            self._current_tag = None
        elif tag == "body" and self._body_depth > 0:
            self._body_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._current_tag == "title":
            self._title_buffer.write(data)
        if self._body_depth > 0:
            normalized = " ".join(data.split())
            if normalized:
                if self.body_text is None:
                    self.body_text = normalized
                else:
                    self.body_text = f"{self.body_text} {normalized}"

    def _capture_meta(self, attributes: Mapping[str, str | None]) -> None:
        name = (attributes.get("name") or attributes.get("property") or "").lower()
        content = attributes.get("content")
        if not content:
            return
        if name in {"description", "og:description"}:
            self.description = content
        elif name in {"author", "article:author"}:
            self.author = content
        elif name in {"article:published_time", "published_time", "pubdate"}:
            self.published_at = content
