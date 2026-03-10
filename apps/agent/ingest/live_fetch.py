from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MVP-Agent/0.1; +https://example.test/local)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}


def fetch_live_payloads_for_source(
    *,
    source: Mapping[str, Any],
    fetched_at_utc: str | None = None,
    timeout_seconds: int = 20,
) -> list[dict[str, Any]]:
    source_type = str(source["type"])
    if source_type != "rss":
        raise ValueError(f"Unsupported live fetch source type: {source_type}")

    request = Request(str(source["url"]), headers=DEFAULT_REQUEST_HEADERS)
    with urlopen(request, timeout=timeout_seconds) as response:
        feed_bytes = response.read()

    feed_text = feed_bytes.decode("utf-8", errors="replace")
    resolved_fetched_at = fetched_at_utc or _utc_now_iso()
    return parse_rss_feed(feed_text=feed_text, fetched_at_utc=resolved_fetched_at)


def parse_rss_feed(*, feed_text: str, fetched_at_utc: str) -> list[dict[str, Any]]:
    root = ET.fromstring(feed_text)
    items = root.findall(".//item")
    if items:
        return [_rss_item_to_payload(item=item, fetched_at_utc=fetched_at_utc) for item in items]

    entries = root.findall(".//{*}entry")
    if entries:
        return [_atom_entry_to_payload(entry=entry, fetched_at_utc=fetched_at_utc) for entry in entries]

    return []


def _rss_item_to_payload(*, item: ET.Element, fetched_at_utc: str) -> dict[str, Any]:
    return {
        "url": _first_text(item, "link"),
        "title": _first_text(item, "title"),
        "author": _first_text(item, "author", "{*}creator"),
        "language": None,
        "published_at": _normalize_timestamp(_first_text(item, "pubDate", "{*}published", "{*}updated")),
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
