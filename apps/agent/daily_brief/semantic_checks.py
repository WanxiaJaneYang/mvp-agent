from __future__ import annotations

QUESTION_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "change",
        "does",
        "few",
        "for",
        "how",
        "in",
        "is",
        "keep",
        "latest",
        "near",
        "next",
        "of",
        "on",
        "or",
        "term",
        "the",
        "this",
        "to",
        "what",
        "weeks",
        "will",
    }
)

TEMPLATED_WHY_IT_MATTERS = frozenset(
    {
        "investors should watch this closely.",
        "investors should watch this closely",
        "this could move markets.",
        "this could move markets",
    }
)


def normalized_issue_tokens(text: str) -> set[str]:
    cleaned = "".join(character.lower() if character.isalnum() else " " for character in text)
    tokens = {token for token in cleaned.split() if token and token not in QUESTION_STOPWORDS}
    if "fed" in tokens:
        tokens.update({"federal", "reserve"})
    if {"federal", "reserve"}.issubset(tokens):
        tokens.add("fed")
    return tokens


def has_watch_issue_anchor(text: str) -> bool:
    normalized_text = text.lower()
    return any(marker in normalized_text for marker in ("falsification", "debate", "issue", "thesis"))
