import unittest

import pandas as pd

from app.scorecard import add_alert_badges, build_anomaly_detail_rows


class ScorecardAlertTests(unittest.TestCase):
    def setUp(self):
        self.metrics = pd.DataFrame(
            {
                "seller_id": ["seller_a"] * 10 + ["seller_b"],
                "total_orders": [10] * 11,
                "late_delivery_rate": [0.05] * 10 + [0.9],
                "average_review_score": [4.5] * 10 + [1.2],
                "negative_review_rate": [0.05] * 10 + [0.95],
                "average_response_time_hours": [12.0] * 10 + [96.0],
                "cancellation_rate_proxy": [0.0] * 10 + [0.5],
                "eligible_for_risk_score": [True] * 11,
                "trust_score": [90.0] * 10 + [25.0],
                "risk_tier": ["Reliable"] * 10 + ["High-Risk"],
            }
        )
        self.order_fact = pd.DataFrame(
            {
                "order_id": ["o1", "o2", "o3"],
                "seller_id": ["seller_b", "seller_b", "seller_b"],
                "order_status": ["delivered", "canceled", "delivered"],
                "purchase_month": ["2024-01", "2024-02", "2024-03"],
                "order_purchase_timestamp": [
                    "2024-01-05",
                    "2024-02-10",
                    "2024-03-15",
                ],
                "is_late_delivery": [0, 1, 1],
                "review_score": [4, 1, 2],
                "response_time_hours": [10.0, 20.0, 72.0],
            }
        )

    def test_add_alert_badges_marks_anomalous_high_risk_seller(self):
        scorecard = add_alert_badges(self.metrics)
        flagged = scorecard[scorecard["seller_id"] == "seller_b"].iloc[0]

        self.assertTrue(flagged["is_anomaly"])
        self.assertEqual(flagged["alert_badge"], "🔴 Anomaly: High-Risk")
        self.assertGreater(flagged["anomaly_count"], 0)

    def test_add_alert_badges_keeps_trusted_badge_for_normal_sellers(self):
        scorecard = add_alert_badges(self.metrics)
        normal = scorecard[scorecard["seller_id"] == "seller_a"].iloc[0]

        self.assertFalse(normal["is_anomaly"])
        self.assertEqual(normal["alert_badge"], "🟢 Trusted")

    def test_build_anomaly_detail_rows_includes_type_and_timestamp(self):
        scorecard = add_alert_badges(self.metrics)
        details = build_anomaly_detail_rows(scorecard, self.order_fact)

        self.assertFalse(details.empty)
        self.assertIn("anomaly_type", details.columns)
        self.assertIn("spike_timestamp", details.columns)
        self.assertIn("2024-", details["spike_timestamp"].iloc[0])


if __name__ == "__main__":
    unittest.main()
