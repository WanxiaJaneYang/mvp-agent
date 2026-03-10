from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from apps.agent.pipeline.identifiers import build_prefixed_uuid_id
from apps.agent.portfolio.input_store import PortfolioPosition


class PortfolioRiskFlag(str, Enum):
    DIRECT_HOLDING = "direct_holding"
    MAPPED_THEME = "mapped_theme"


@dataclass(frozen=True)
class PortfolioRelevanceFlag:
    relevance_id: str
    synthesis_id: str
    ticker: str
    relevance_score: float
    risk_flag: str
    rationale: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


DEFAULT_TICKER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "BND": ("bond", "credit", "treasury", "yield"),
    "GLD": ("gold", "bullion", "commodity", "inflation"),
    "QQQ": ("technology", "nasdaq", "growth", "semiconductor", "ai"),
    "SPY": ("equity", "stocks", "s&p", "large cap"),
    "TLT": ("treasury", "rates", "duration", "yield", "inflation"),
    "VOO": ("equity", "stocks", "s&p", "large cap"),
    "VTI": ("equity", "stocks", "market", "large cap"),
    "VXUS": ("international", "europe", "asia", "fx"),
}
DEFAULT_TICKER_ALIASES: dict[str, tuple[str, ...]] = {
    "QQQ": ("invesco qqq", "nasdaq-100", "nasdaq 100"),
    "SPY": ("spdr s&p 500", "s&p 500"),
    "TLT": ("20+ year treasury", "long treasury"),
    "VOO": ("vanguard s&p 500", "s&p 500"),
    "VTI": ("total stock market", "us equities"),
}
ASSET_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "bond": ("bond", "treasury", "yield", "duration", "rates"),
    "commodity": ("commodity", "gold", "oil", "metals"),
    "equity": ("equity", "stocks", "earnings", "market"),
    "etf": (),
}


def build_portfolio_relevance_flags(
    *,
    positions: Iterable[PortfolioPosition],
    documents: Iterable[Mapping[str, Any]],
    synthesis: Mapping[str, Any],
    synthesis_id: str,
    generated_at_utc: str,
) -> list[PortfolioRelevanceFlag]:
    corpus_text = _build_corpus_text(documents=documents, synthesis=synthesis)
    flags: list[PortfolioRelevanceFlag] = []

    for position in positions:
        direct_match = _has_direct_match(position=position, corpus_text=corpus_text)
        matched_keywords = _matched_keywords(position=position, corpus_text=corpus_text)
        if not direct_match and not matched_keywords:
            continue

        base_score = 70.0 if direct_match else 45.0
        keyword_bonus = min(len(matched_keywords) * 7.5, 22.5)
        weight_bonus = min(position.weight_pct * 0.30, 15.0)
        relevance_score = round(min(100.0, base_score + keyword_bonus + weight_bonus), 1)
        risk_flag = (
            PortfolioRiskFlag.DIRECT_HOLDING.value
            if direct_match
            else PortfolioRiskFlag.MAPPED_THEME.value
        )
        rationale = _build_rationale(
            position=position,
            direct_match=direct_match,
            matched_keywords=matched_keywords,
        )
        flags.append(
            PortfolioRelevanceFlag(
                relevance_id=build_prefixed_uuid_id("relevance", synthesis_id, position.ticker),
                synthesis_id=synthesis_id,
                ticker=position.ticker,
                relevance_score=relevance_score,
                risk_flag=risk_flag,
                rationale=rationale,
                created_at=generated_at_utc,
            )
        )

    return sorted(flags, key=lambda flag: (-flag.relevance_score, flag.ticker))


def _build_corpus_text(
    *,
    documents: Iterable[Mapping[str, Any]],
    synthesis: Mapping[str, Any],
) -> str:
    text_parts: list[str] = []
    for document in documents:
        for field in ("title", "rss_snippet", "body_text"):
            value = document.get(field)
            if value:
                text_parts.append(str(value))
    for bullets in synthesis.values():
        if not isinstance(bullets, list):
            continue
        for bullet in bullets:
            if isinstance(bullet, Mapping) and bullet.get("text"):
                text_parts.append(str(bullet["text"]))
    return " ".join(text_parts).lower()


def _has_direct_match(*, position: PortfolioPosition, corpus_text: str) -> bool:
    for term in (position.ticker, *DEFAULT_TICKER_ALIASES.get(position.ticker, ())):
        normalized = term.strip().lower()
        if not normalized:
            continue
        if re.search(rf"\b{re.escape(normalized)}\b", corpus_text):
            return True
    return False


def _matched_keywords(*, position: PortfolioPosition, corpus_text: str) -> list[str]:
    keywords = set(DEFAULT_TICKER_KEYWORDS.get(position.ticker, ()))
    keywords.update(ASSET_TYPE_KEYWORDS.get(position.asset_type, ()))
    keywords.update(_note_keywords(position.notes))
    return sorted(keyword for keyword in keywords if keyword and keyword.lower() in corpus_text)


def _note_keywords(notes: str | None) -> set[str]:
    if notes is None:
        return set()
    return {
        keyword.strip().lower()
        for keyword in re.split(r"[,;\n/|]+", notes)
        if keyword.strip()
    }


def _build_rationale(
    *,
    position: PortfolioPosition,
    direct_match: bool,
    matched_keywords: list[str],
) -> str:
    fragments: list[str] = []
    if direct_match:
        fragments.append(f"Matched direct holding references for {position.ticker}.")
    if matched_keywords:
        fragments.append(
            "Matched portfolio mapping terms: " + ", ".join(matched_keywords[:3]) + "."
        )
    if not fragments:
        fragments.append(f"Matched {position.ticker} through portfolio context.")
    return " ".join(fragments)
