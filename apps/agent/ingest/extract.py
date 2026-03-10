from __future__ import annotations

import base64
from io import BytesIO
from collections.abc import Mapping
from typing import Any

from pypdf import PdfReader


def extract_payload(*, source: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    source_type = source["type"]
    if source_type == "rss":
        return _extract_rss_payload(source=source, payload=payload)
    if source_type == "html":
        return _extract_html_payload(source=source, payload=payload)
    if source_type == "pdf":
        return _extract_pdf_payload(source=source, payload=payload)
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


def _extract_pdf_payload(*, source: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    canonical_url = payload.get("canonical_url", payload.get("url"))
    if not canonical_url:
        raise ValueError("PDF payload must include canonical_url or url")

    return {
        "publisher": source["name"],
        "canonical_url": canonical_url,
        "title": payload.get("title"),
        "author": payload.get("author"),
        "language": payload.get("language"),
        "published_at": payload.get("published_at"),
        "fetched_at": payload.get("fetched_at"),
        "rss_snippet": payload.get("summary", payload.get("snippet")),
        "body_text": _extract_pdf_text(payload=payload),
        "doc_type": payload.get("doc_type", "report"),
    }


def _extract_pdf_text(*, payload: Mapping[str, Any]) -> str | None:
    if payload.get("text") is not None:
        return str(payload["text"])
    if payload.get("body_text") is not None:
        return str(payload["body_text"])

    pdf_bytes = _load_pdf_bytes(payload=payload)
    if pdf_bytes is None:
        raise ValueError("PDF payload must include text, body_text, pdf_bytes, or pdf_base64")

    reader = PdfReader(BytesIO(pdf_bytes))
    page_text = [(page.extract_text() or "").strip() for page in reader.pages]
    normalized_pages = [text for text in page_text if text]
    if not normalized_pages:
        return None
    return "\n\n".join(normalized_pages)


def _load_pdf_bytes(*, payload: Mapping[str, Any]) -> bytes | None:
    raw_bytes = payload.get("pdf_bytes")
    if isinstance(raw_bytes, bytes):
        return raw_bytes

    base64_text = payload.get("pdf_base64")
    if isinstance(base64_text, str):
        return base64.b64decode(base64_text.encode("ascii"))

    return None
