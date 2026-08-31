import unittest

import pandas as pd

from app.signals import (
    build_cohort_comparison,
    build_correlation_heatmap,
    build_monthly_sentiment_bar,
    build_performance_decay_chart,
    build_return_rate_scatter,
    build_trust_score_trend,
    prepare_monthly_seller_metrics,
    prepare_signal_metrics,
)


class BehaviourSignalTests(unittest.TestCase):
    def setUp(self):
        self.metrics = pd.DataFrame(
            {
                "seller_id": ["seller_a", "seller_b", "seller_c"],
                "total_orders": [15, 12, 2],
                "late_delivery_rate": [0.0, 0.8, 0.1],
                "average_review_score": [5.0, 2.0, 4.5],
                "negative_review_rate": [0.0, 0.7, 0.0],
                "average_response_time_hours": [8.0, 72.0, 14.0],
                "cancellation_rate_proxy": [0.0, 0.5, 0.0],
                "eligible_for_risk_score": [True, True, False],
                "risk_tier": ["Reliable", "High-Risk", "Insufficient Data"],
            }
        )
        self.order_fact = pd.DataFrame(
            {
                "order_id": ["o1", "o2", "o3", "o4", "o5"],
                "seller_id": ["seller_a", "seller_a", "seller_b", "seller_b", "seller_b"],
                "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered"],
                "purchase_month": ["2024-01", "2024-02", "2024-01", "2024-02", "2024-03"],
                "order_purchase_timestamp": [
                    "2024-01-03",
                    "2024-02-10",
                    "2024-01-12",
                    "2024-02-15",
                    "2024-03-20",
                ],
                "is_late_delivery": [0, 0, 0, 1, 1],
                "delivery_delay_days": [0.0, 0.0, 0.0, 4.0, 6.0],
                "review_score": [5, 5, 4, 2, 1],
                "response_time_hours": [8.0, 9.0, 12.0, 30.0, 48.0],
                "sentiment_bucket": [
                    "positive",
                    "positive",
                    "positive",
                    "negative",
                    "negative",
                ],
            }
        )

    def test_prepare_signal_metrics_scores_and_filters_eligible_sellers(self):
        prepared = prepare_signal_metrics(self.metrics)

        self.assertEqual(prepared["seller_id"].tolist(), ["seller_a", "seller_b"])
        self.assertIn("trust_score", prepared.columns)
        self.assertTrue(prepared["trust_score"].notna().all())

    def test_return_rate_scatter_is_plotly_figure_with_hover_data(self):
        prepared = prepare_signal_metrics(self.metrics)

        fig = build_return_rate_scatter(prepared)

        self.assertEqual(fig.layout.title.text, "Return Rate Proxy vs Trust Score")
        self.assertGreater(len(fig.data), 0)
        hovertemplate = fig.data[0].hovertemplate or ""
        self.assertIn("seller_id", hovertemplate)
        self.assertEqual(fig.layout.xaxis.tickformat, ".0%")

    def test_correlation_heatmap_contains_risk_signal_matrix(self):
        prepared = prepare_signal_metrics(self.metrics)

        fig = build_correlation_heatmap(prepared)

        self.assertEqual(fig.layout.title.text, "Risk Signal Correlation Heatmap")
        self.assertGreater(len(fig.data[0].z), 0)

    def test_cohort_comparison_summarises_high_and_low_trust(self):
        prepared = prepare_signal_metrics(self.metrics)

        summary = build_cohort_comparison(prepared)

        self.assertEqual(summary["trust_cohort"].astype(str).tolist(), ["Low Trust", "High Trust"])
        self.assertEqual(summary.loc[summary["trust_cohort"] == "High Trust", "sellers"].iloc[0], 1)
        self.assertIn("avg_negative_sentiment", summary.columns)

    def test_prepare_monthly_seller_metrics_scores_each_seller_month(self):
        monthly = prepare_monthly_seller_metrics(self.order_fact)

        self.assertIn("trust_score", monthly.columns)
        self.assertEqual(
            monthly[["seller_id", "purchase_month"]].drop_duplicates().shape[0],
            5,
        )
        self.assertTrue(monthly["trust_score"].notna().all())

    def test_trust_score_trend_is_interactive_plotly_line(self):
        monthly = prepare_monthly_seller_metrics(self.order_fact)

        fig = build_trust_score_trend(monthly)

        self.assertEqual(fig.layout.title.text, "Seller Trust Score Trend Over Time")
        self.assertEqual(fig.data[0].mode, "lines+markers")
        self.assertIn("Orders", fig.data[0].hovertemplate)

    def test_monthly_sentiment_bar_stacks_sentiment_by_month(self):
        fig = build_monthly_sentiment_bar(self.order_fact)

        self.assertEqual(fig.layout.title.text, "Monthly Sentiment Distribution")
        self.assertGreater(len(fig.data), 0)
        self.assertEqual(fig.layout.barmode, "stack")

    def test_performance_decay_chart_shows_declining_sellers(self):
        monthly = prepare_monthly_seller_metrics(self.order_fact)

        fig = build_performance_decay_chart(monthly)

        self.assertEqual(fig.layout.title.text, "Seller Performance Decay")
        self.assertGreater(len(fig.data), 0)
        self.assertIn("Trust Score Change", fig.layout.xaxis.title.text)


if __name__ == "__main__":
    unittest.main()
