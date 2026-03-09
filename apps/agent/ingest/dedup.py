from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def classify_duplicate(
    *,
    candidate: Mapping[str, Any],
    existing_documents: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    candidate_url = candidate.get("canonical_url")
    candidate_hash = candidate.get("content_hash")

    for document in existing_documents:
        if candidate_url and document.get("canonical_url") == candidate_url:
            return {
                "is_duplicate": True,
                "reason": "canonical_url",
                "matched_doc_id": document.get("doc_id"),
            }

    for document in existing_documents:
        if candidate_hash and document.get("content_hash") == candidate_hash:
            return {
                "is_duplicate": True,
                "reason": "content_hash",
                "matched_doc_id": document.get("doc_id"),
            }

    return {
        "is_duplicate": False,
        "reason": None,
        "matched_doc_id": None,
    }
