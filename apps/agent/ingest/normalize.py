from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any


def build_document_record(*, source: Mapping[str, Any], extracted: Mapping[str, Any]) -> dict[str, Any]:
    paywall_policy = source["paywall_policy"]
    metadata_only = int(paywall_policy == "metadata_only")
    body_text = None if metadata_only else extracted.get("body_text")
    fetched_at = extracted["fetched_at"]

    return {
        "source_id": source["id"],
        "publisher": extracted.get("publisher", source["name"]),
        "canonical_url": extracted["canonical_url"],
        "title": extracted.get("title"),
        "author": extracted.get("author"),
        "language": extracted.get("language"),
        "doc_type": extracted.get("doc_type"),
        "published_at": extracted.get("published_at"),
        "fetched_at": fetched_at,
        "paywall_policy": paywall_policy,
        "metadata_only": metadata_only,
        "rss_snippet": extracted.get("rss_snippet"),
        "body_text": body_text,
        "content_hash": _build_content_hash(
            canonical_url=extracted["canonical_url"],
            title=extracted.get("title"),
            rss_snippet=extracted.get("rss_snippet"),
            body_text=body_text,
        ),
        "status": "active",
        "created_at": fetched_at,
        "updated_at": fetched_at,
    }


def _build_content_hash(
    *,
    canonical_url: str,
    title: str | None,
    rss_snippet: str | None,
    body_text: str | None,
) -> str:
    digest = hashlib.sha256()
    for value in (canonical_url, title, rss_snippet, body_text):
        digest.update((value or "").encode("utf-8"))
        digest.update(b"\x1f")
    return digest.hexdigest()
