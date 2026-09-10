import unittest

import plotly.graph_objects as go

from app.theme import (
    HIGH_RISK_RED,
    RISK_TIER_COLORS,
    SENTIMENT_COLORS,
    TRUSTED_GREEN,
    WATCHLIST_YELLOW,
    apply_chart_polish,
)


class DashboardThemeTests(unittest.TestCase):
    def test_risk_and_sentiment_colors_follow_prd_scheme(self):
        self.assertEqual(RISK_TIER_COLORS["Reliable"], TRUSTED_GREEN)
        self.assertEqual(RISK_TIER_COLORS["Watchlist"], WATCHLIST_YELLOW)
        self.assertEqual(RISK_TIER_COLORS["Return-Prone"], WATCHLIST_YELLOW)
        self.assertEqual(RISK_TIER_COLORS["High-Risk"], HIGH_RISK_RED)
        self.assertEqual(SENTIMENT_COLORS["positive"], TRUSTED_GREEN)
        self.assertEqual(SENTIMENT_COLORS["neutral"], WATCHLIST_YELLOW)
        self.assertEqual(SENTIMENT_COLORS["negative"], HIGH_RISK_RED)

    def test_chart_polish_adds_responsive_layout_defaults(self):
        fig = apply_chart_polish(go.Figure(), height=360, showlegend=False)

        self.assertEqual(fig.layout.height, 360)
        self.assertEqual(fig.layout.showlegend, False)
        self.assertEqual(fig.layout.template.layout.paper_bgcolor, "white")
        self.assertEqual(fig.layout.xaxis.automargin, True)
        self.assertEqual(fig.layout.yaxis.automargin, True)
        self.assertEqual(fig.layout.uniformtext.mode, "hide")


if __name__ == "__main__":
    unittest.main()

