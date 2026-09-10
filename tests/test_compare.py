import unittest

import pandas as pd

from app.compare import (
    build_difference_highlights,
    build_risk_badge_summary,
    build_risk_profile_chart,
    build_side_by_side_table,
    build_trust_overlay_chart,
    get_seller_options,
    prepare_compare_metrics,
)


class CompareSellersTests(unittest.TestCase):
    def setUp(self):
        self.metrics = pd.DataFrame(
            {
                "seller_id": ["seller_good", "seller_watch", "seller_bad"],
                "risk_tier": ["Reliable", "Inconsistent", "High-Risk"],
                "trust_score": [92.0, 68.0, 35.0],
                "total_orders": [40, 30, 25],
                "cancellation_rate_proxy": [0.01, 0.08, 0.25],
                "negative_review_rate": [0.02, 0.15, 0.55],
                "late_delivery_rate": [0.03, 0.22, 0.70],
                "average_review_score": [4.8, 3.7, 2.1],
                "average_response_time_hours": [8.0, 24.0, 60.0],
            }
        )
        self.monthly = pd.DataFrame(
            {
                "seller_id": ["seller_good", "seller_good", "seller_bad", "seller_bad"],
                "purchase_month": pd.to_datetime(["2024-01", "2024-02", "2024-01", "2024-02"]),
                "trust_score": [95.0, 92.0, 50.0, 35.0],
                "total_orders": [20, 20, 10, 15],
                "average_review_score": [4.9, 4.8, 2.7, 2.1],
                "negative_review_rate": [0.0, 0.02, 0.4, 0.55],
            }
        )

    def test_seller_options_prioritise_lowest_trust_scores(self):
        self.assertEqual(
            get_seller_options(self.metrics),
            ["seller_bad", "seller_watch", "seller_good"],
        )

    def test_prepare_compare_metrics_filters_selected_sellers(self):
        result = prepare_compare_metrics(self.metrics, ["seller_good", "seller_bad"])

        self.assertEqual(result["seller_id"].tolist(), ["seller_bad", "seller_good"])
        self.assertIn("trust_score", result.columns)
        self.assertIn("late_delivery_rate", result.columns)

    def test_side_by_side_table_formats_counts_percentages_and_scores(self):
        selected = prepare_compare_metrics(self.metrics, ["seller_good", "seller_bad"])
        table = build_side_by_side_table(selected)

        self.assertIn("seller_good", table.columns)
        self.assertIn("seller_bad", table.columns)
        self.assertIn("Return Rate Proxy", table["Metric"].tolist())
        self.assertIn("25.0%", table.to_string())
        self.assertIn("40", table.to_string())

    def test_difference_highlights_show_metric_gaps(self):
        selected = prepare_compare_metrics(self.metrics, ["seller_good", "seller_bad"])
        differences = build_difference_highlights(selected)

        self.assertIn("Highest Seller", differences.columns)
        self.assertIn("Gap", differences.columns)
        risk_gap = differences[differences["Metric"] == "Late Delivery Rate"].iloc[0]
        self.assertEqual(risk_gap["Highest Seller"], "seller_bad")
        self.assertEqual(risk_gap["Gap"], "67.0%")

    def test_risk_profile_chart_compares_selected_sellers(self):
        selected = prepare_compare_metrics(self.metrics, ["seller_good", "seller_bad"])
        fig = build_risk_profile_chart(selected)

        self.assertEqual(fig.layout.title.text, "Risk Profile Comparison")
        self.assertGreater(len(fig.data), 0)
        self.assertEqual(fig.layout.yaxis.tickformat, ".0%")

    def test_trust_overlay_chart_uses_selected_seller_lines(self):
        fig = build_trust_overlay_chart(self.monthly)

        self.assertEqual(fig.layout.title.text, "Selected Sellers Trust Score Overlay")
        self.assertGreaterEqual(len(fig.data), 2)
        self.assertIn("seller_good", {trace.name for trace in fig.data})

    def test_risk_badge_summary_includes_theme_color(self):
        selected = prepare_compare_metrics(self.metrics, ["seller_bad"])
        summary = build_risk_badge_summary(selected)

        self.assertEqual(summary.iloc[0]["risk_color"], "#d62728")


if __name__ == "__main__":
    unittest.main()
