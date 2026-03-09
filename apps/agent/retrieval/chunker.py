from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


def chunk_document(*, document: Mapping[str, Any], max_chars: int = 800) -> list[dict[str, int | str]]:
    if document.get("metadata_only") or not document.get("body_text"):
        return []

    body_text = str(document["body_text"])
    words = list(re.finditer(r"\S+", body_text))
    if not words:
        return []

    chunks: list[dict[str, int | str]] = []
    current_words: list[re.Match[str]] = []

    for word in words:
        if not current_words:
            current_words.append(word)
            continue

        proposed_start = current_words[0].start()
        proposed_end = word.end()
        if proposed_end - proposed_start >= max_chars:
            chunks.append(_build_chunk(body_text=body_text, chunk_index=len(chunks), words=current_words))
            current_words = [word]
            continue

        current_words.append(word)

    if current_words:
        chunks.append(_build_chunk(body_text=body_text, chunk_index=len(chunks), words=current_words))

    return chunks


def _build_chunk(
    *,
    body_text: str,
    chunk_index: int,
    words: list[re.Match[str]],
) -> dict[str, int | str]:
    char_start = words[0].start()
    char_end = words[-1].end()
    return {
        "chunk_index": chunk_index,
        "text": body_text[char_start:char_end],
        "char_start": char_start,
        "char_end": char_end,
    }
