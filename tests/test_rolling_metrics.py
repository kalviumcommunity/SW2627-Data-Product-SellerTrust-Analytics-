import unittest

import pandas as pd

from src.rolling_metrics import compute_rolling_metrics


def _make_order_fact() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3", "o4", "o5", "o6"],
            "seller_id": ["s1", "s1", "s1", "s1", "s1", "s2"],
            "order_status": ["delivered", "delivered", "canceled", "delivered", "delivered", "delivered"],
            "purchase_month": ["2024-01", "2024-01", "2024-02", "2024-02", "2024-03", "2024-01"],
            "order_purchase_timestamp": [
                "2024-01-05", "2024-01-15", "2024-02-10", "2024-02-20", "2024-03-10", "2024-01-12",
            ],
            "review_score": [5, 4, 2, 3, 5, 4],
            "is_late_delivery": [0, 0, 1, 0, 0, 0],
            "delivery_delay_days": [0.0, 0.0, 3.0, 0.0, 0.0, 0.0],
        }
    )


class RollingMetricsTests(unittest.TestCase):
    def test_empty_input_returns_empty_dataframe(self):
        result = compute_rolling_metrics(pd.DataFrame())
        self.assertEqual(len(result), 0)
        self.assertIn("rolling_avg_review_score", result.columns)

    def test_output_contains_expected_columns(self):
        result = compute_rolling_metrics(_make_order_fact())
        expected_cols = [
            "seller_id",
            "purchase_month",
            "rolling_avg_review_score",
            "rolling_cancellation_rate",
            "rolling_late_delivery_rate",
            "window_size",
        ]
        for col in expected_cols:
            self.assertIn(col, result.columns)

    def test_rolling_metrics_computed_per_seller(self):
        result = compute_rolling_metrics(_make_order_fact())
        sellers = result["seller_id"].unique()
        self.assertIn("s1", sellers)
        self.assertIn("s2", sellers)

    def test_rolling_review_score_is_average(self):
        result = compute_rolling_metrics(_make_order_fact())
        s1_jan = result[(result["seller_id"] == "s1") & (result["purchase_month"] == "2024-01-01")]
        self.assertAlmostEqual(s1_jan["rolling_avg_review_score"].iloc[0], 4.5)

    def test_rolling_cancellation_rate(self):
        result = compute_rolling_metrics(_make_order_fact())
        s1_feb = result[(result["seller_id"] == "s1") & (result["purchase_month"] == "2024-02-01")]
        self.assertGreater(s1_feb["rolling_cancellation_rate"].iloc[0], 0)

    def test_window_size_uses_available_data(self):
        fact = _make_order_fact()
        result = compute_rolling_metrics(fact, window_days=30)
        s1 = result[result["seller_id"] == "s1"]
        self.assertTrue((s1["window_size"] <= 30).all())

    def test_sparse_seller_gets_expanding_window(self):
        fact = pd.DataFrame(
            {
                "order_id": ["o1", "o2"],
                "seller_id": ["s_sparse", "s_sparse"],
                "order_status": ["delivered", "delivered"],
                "purchase_month": ["2024-01", "2024-06"],
                "order_purchase_timestamp": ["2024-01-10", "2024-06-10"],
                "review_score": [5, 3],
                "is_late_delivery": [0, 1],
                "delivery_delay_days": [0.0, 2.0],
            }
        )
        result = compute_rolling_metrics(fact, window_days=30)
        self.assertEqual(len(result), 2)
        self.assertEqual(result["rolling_avg_review_score"].iloc[0], 5.0)
        self.assertEqual(result["rolling_avg_review_score"].iloc[1], 4.0)

    def test_single_order_seller(self):
        fact = pd.DataFrame(
            {
                "order_id": ["o1"],
                "seller_id": ["s_single"],
                "order_status": ["delivered"],
                "purchase_month": ["2024-01"],
                "order_purchase_timestamp": ["2024-01-10"],
                "review_score": [5],
                "is_late_delivery": [0],
                "delivery_delay_days": [0.0],
            }
        )
        result = compute_rolling_metrics(fact)
        self.assertEqual(len(result), 1)
        self.assertEqual(result["rolling_avg_review_score"].iloc[0], 5.0)


if __name__ == "__main__":
    unittest.main()
