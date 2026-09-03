import unittest

import pandas as pd

from app.segments import (
    SEGMENT_ORDER,
    build_segment_composition_chart,
    build_segment_summary,
    prepare_segment_metrics,
)


class BehaviourSegmentsTests(unittest.TestCase):
    def setUp(self):
        self.metrics = pd.DataFrame(
            {
                "seller_id": ["s1", "s2", "s3", "s4"],
                "total_orders": [20, 20, 20, 1],
                "late_delivery_rate": [0.0, 0.2, 0.5, 0.0],
                "average_review_score": [5.0, 3.5, 2.0, 5.0],
                "negative_review_rate": [0.0, 0.2, 0.6, 0.0],
                "average_response_time_hours": [10.0, 24.0, 60.0, 5.0],
                "cancellation_rate_proxy": [0.0, 0.1, 0.3, 0.0],
                "eligible_for_risk_score": [True, True, True, False],
                "risk_tier": ["Reliable", "Inconsistent", "High-Risk", "Insufficient Data"],
            }
        )

    def test_prepare_segment_metrics_excludes_insufficient_data(self):
        prepared = prepare_segment_metrics(self.metrics)

        self.assertEqual(prepared["seller_id"].tolist(), ["s1", "s2", "s3"])
        self.assertNotIn("Insufficient Data", prepared["risk_tier"].tolist())

    def test_segment_summary_returns_all_segment_rows_in_order(self):
        summary = build_segment_summary(self.metrics)

        self.assertEqual(summary["risk_tier"].tolist(), SEGMENT_ORDER)
        self.assertEqual(summary["sellers"].sum(), 3)
        self.assertIn("avg_late_delivery_rate", summary.columns)

    def test_segment_composition_chart_is_plotly_bar(self):
        fig = build_segment_composition_chart(self.metrics)

        self.assertEqual(fig.layout.title.text, "Seller Behaviour Segment Composition")
        self.assertGreater(len(fig.data), 0)
        self.assertEqual(fig.layout.showlegend, False)


if __name__ == "__main__":
    unittest.main()
