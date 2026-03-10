import unittest

from apps.agent.portfolio.input_store import PortfolioPosition
from apps.agent.portfolio.relevance import build_portfolio_relevance_flags


class PortfolioRelevanceTests(unittest.TestCase):
    def test_build_portfolio_relevance_flags_uses_direct_ticker_and_manual_notes(self):
        flags = build_portfolio_relevance_flags(
            positions=[
                PortfolioPosition(
                    ticker="QQQ",
                    weight_pct=25.0,
                    asset_type="etf",
                    notes="technology, ai, semiconductors",
                ),
                PortfolioPosition(
                    ticker="TLT",
                    weight_pct=15.0,
                    asset_type="bond",
                    notes="treasury, rates, duration",
                ),
            ],
            documents=[
                {
                    "title": "QQQ investors brace for another semiconductor-heavy session",
                    "rss_snippet": "Mega-cap technology and AI demand kept lifting semiconductor shares.",
                    "body_text": "QQQ and other growth funds remained tied to AI and semiconductor news.",
                },
                {
                    "title": "Treasury yields slip as Fed rate path cools",
                    "rss_snippet": "Long-duration bond funds reacted to softer rate expectations.",
                    "body_text": "Treasury duration benefited as investors priced fewer Fed hikes.",
                },
            ],
            synthesis={
                "watch": [
                    {
                        "text": "Watch whether Treasury yields keep falling if rate expectations ease further.",
                        "citation_ids": ["cite_002"],
                    }
                ]
            },
            synthesis_id="syn_portfolio_1",
            generated_at_utc="2026-03-10T16:00:00Z",
        )

        tickers = [flag.ticker for flag in flags]
        self.assertEqual(tickers, ["QQQ", "TLT"])
        self.assertEqual(flags[0].risk_flag, "direct_holding")
        self.assertEqual(flags[1].risk_flag, "mapped_theme")
        self.assertGreater(flags[0].relevance_score, flags[1].relevance_score)

    def test_build_portfolio_relevance_flags_returns_empty_when_no_position_matches(self):
        flags = build_portfolio_relevance_flags(
            positions=[PortfolioPosition(ticker="GLD", weight_pct=10.0, asset_type="commodity")],
            documents=[
                {
                    "title": "Regional banks digest new capital rules",
                    "rss_snippet": "Bank capital and regulation remained the focus.",
                    "body_text": "Regional bank capital and regulation remained the focus.",
                }
            ],
            synthesis={},
            synthesis_id="syn_portfolio_2",
            generated_at_utc="2026-03-10T16:00:00Z",
        )

        self.assertEqual(flags, [])


if __name__ == "__main__":
    unittest.main()
