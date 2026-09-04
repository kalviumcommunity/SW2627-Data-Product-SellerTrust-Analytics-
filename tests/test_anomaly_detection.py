import unittest

import pandas as pd

from src.anomaly_detection import (
    compute_seller_anomalies,
    detect_iqr_outliers,
    detect_zscore_anomalies,
)


def _make_sellers() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "seller_id": ["s_normal"] * 10 + ["s_anomalous"],
            "total_orders": [10] * 10 + [8],
            "late_delivery_rate": [0.05] * 10 + [0.9],
            "average_review_score": [4.0] * 10 + [1.2],
            "negative_review_rate": [0.1] * 10 + [0.95],
            "cancellation_rate_proxy": [0.01] * 10 + [0.4],
            "average_response_time_hours": [60.0] * 10 + [1200.0],
            "eligible_for_risk_score": [True] * 11,
        }
    )


class AnomalyDetectionTests(unittest.TestCase):
    def test_iqr_detects_outlier_in_high_value(self):
        series = pd.Series([1, 2, 1, 3, 2, 1, 3, 2, 1, 50])
        flags = detect_iqr_outliers(series)
        self.assertTrue(flags.iloc[-1])
        self.assertFalse(flags.iloc[0])

    def test_iqr_no_outliers_for_uniform_data(self):
        series = pd.Series([5, 5, 5, 5, 5])
        flags = detect_iqr_outliers(series)
        self.assertFalse(flags.any())

    def test_zscore_detects_extreme_value(self):
        series = pd.Series([1, 2, 2, 3, 2, 2, 3, 2, 2, 50])
        flags = detect_zscore_anomalies(series, threshold=2.5)
        self.assertTrue(flags.iloc[-1])
        self.assertFalse(flags.iloc[0])

    def test_zscore_no_outliers_for_normal_data(self):
        series = pd.Series([10, 11, 9, 10, 12, 8, 10, 11, 9, 10])
        flags = detect_zscore_anomalies(series, threshold=3.0)
        self.assertFalse(flags.any())

    def test_zscore_zero_std_produces_no_outliers(self):
        series = pd.Series([5, 5, 5, 5, 5])
        flags = detect_zscore_anomalies(series)
        self.assertFalse(flags.any())

    def test_compute_seller_anomalies_flags_extreme_sellers(self):
        sellers = _make_sellers()
        result = compute_seller_anomalies(sellers)

        anomalous = result[result["seller_id"] == "s_anomalous"].iloc[0]
        self.assertTrue(anomalous["any_anomaly"])
        self.assertGreater(anomalous["anomaly_count"], 0)

        normals = result[result["seller_id"] == "s_normal"]
        self.assertFalse(normals["any_anomaly"].any())

    def test_compute_seller_anomalies_includes_per_metric_flags(self):
        sellers = _make_sellers()
        result = compute_seller_anomalies(sellers)

        self.assertIn("late_delivery_rate_iqr_outlier", result.columns)
        self.assertIn("late_delivery_rate_zscore_anomaly", result.columns)
        self.assertIn("average_review_score_iqr_outlier", result.columns)

    def test_compute_seller_anomalies_anomaly_count(self):
        sellers = _make_sellers()
        result = compute_seller_anomalies(sellers)
        anomalous = result[result["seller_id"] == "s_anomalous"].iloc[0]
        self.assertGreaterEqual(anomalous["anomaly_count"], 1)


if __name__ == "__main__":
    unittest.main()
