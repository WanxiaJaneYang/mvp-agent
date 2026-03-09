from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def extract_payload(*, source: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    source_type = source["type"]
    if source_type == "rss":
        return _extract_rss_payload(source=source, payload=payload)
    if source_type == "html":
        return _extract_html_payload(source=source, payload=payload)
    raise ValueError(f"Unsupported source type: {source_type}")


def _extract_rss_payload(*, source: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "publisher": source["name"],
        "canonical_url": payload["url"],
        "title": payload.get("title"),
        "author": payload.get("author"),
        "language": payload.get("language"),
        "published_at": payload.get("published_at"),
        "fetched_at": payload.get("fetched_at"),
        "rss_snippet": payload.get("summary"),
        "body_text": payload.get("body_text"),
        "doc_type": payload.get("doc_type"),
    }


def _extract_html_payload(*, source: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "publisher": source["name"],
        "canonical_url": payload["canonical_url"],
        "title": payload.get("headline", payload.get("title")),
        "author": payload.get("byline", payload.get("author")),
        "language": payload.get("language"),
        "published_at": payload.get("published_at"),
        "fetched_at": payload.get("fetched_at"),
        "rss_snippet": payload.get("snippet", payload.get("summary")),
        "body_text": payload.get("text", payload.get("body_text")),
        "doc_type": payload.get("doc_type"),
    }
