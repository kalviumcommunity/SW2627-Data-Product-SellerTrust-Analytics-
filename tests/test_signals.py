import unittest

import pandas as pd

from app.signals import (
    build_cohort_comparison,
    build_correlation_heatmap,
    build_return_rate_scatter,
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


if __name__ == "__main__":
    unittest.main()
