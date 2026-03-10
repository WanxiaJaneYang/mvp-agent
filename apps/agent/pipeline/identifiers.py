from __future__ import annotations

import uuid


_SEPARATOR = "\x1f"


def build_prefixed_uuid_id(prefix: str, *parts: object) -> str:
    if not prefix:
        raise ValueError("prefix must be a non-empty string")
    if not parts:
        raise ValueError("at least one identity part is required")

    material = _SEPARATOR.join(str(part) for part in parts)
    return f"{prefix}_{uuid.uuid5(uuid.NAMESPACE_URL, material)}"


def build_document_id(*, canonical_url: str) -> str:
    return build_prefixed_uuid_id("doc", canonical_url)


def build_chunk_id(*, doc_id: str, chunk_index: int) -> str:
    return build_prefixed_uuid_id("chunk", doc_id, chunk_index)


def build_synthesis_id(*, run_id: str) -> str:
    return build_prefixed_uuid_id("syn", run_id)


def build_pack_id(*, run_id: str, query_text: str) -> str:
    return build_prefixed_uuid_id("pack", run_id, query_text)


def build_citation_id(
    *,
    source_id: str,
    doc_id: str,
    chunk_id: str,
    url: str,
) -> str:
    return build_prefixed_uuid_id("cite", source_id, doc_id, chunk_id, url)
