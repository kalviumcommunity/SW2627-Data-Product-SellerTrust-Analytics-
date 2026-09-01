import unittest

import pandas as pd

from src.anomaly_detection import (
    build_anomaly_summary,
    detect_anomalies,
    detect_iqr_outliers,
    detect_z_score_outliers,
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
        series = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 100])
        flags = detect_iqr_outliers(series)
        self.assertTrue(flags.iloc[-1])
        self.assertFalse(flags.iloc[0])

    def test_iqr_no_outliers_for_uniform_data(self):
        series = pd.Series([5, 5, 5, 5, 5])
        flags = detect_iqr_outliers(series)
        self.assertFalse(flags.any())

    def test_zscore_detects_extreme_value(self):
        series = pd.Series([1, 2, 2, 3, 2, 2, 3, 2, 2, 50])
        flags = detect_z_score_outliers(series, threshold=2.5)
        self.assertTrue(flags.iloc[-1])
        self.assertFalse(flags.iloc[0])

    def test_zscore_no_outliers_for_normal_data(self):
        series = pd.Series([10, 11, 9, 10, 12, 8, 10, 11, 9, 10])
        flags = detect_z_score_outliers(series, threshold=3.0)
        self.assertFalse(flags.any())

    def test_zscore_zero_std_produces_no_outliers(self):
        series = pd.Series([5, 5, 5, 5, 5])
        flags = detect_z_score_outliers(series)
        self.assertFalse(flags.any())

    def test_detect_anomalies_flags_sellers_with_extreme_metrics(self):
        sellers = _make_sellers()
        result = detect_anomalies(sellers)

        anomalous = result[result["seller_id"] == "s_anomalous"].iloc[0]
        self.assertTrue(anomalous["is_anomaly"])
        self.assertGreater(anomalous["anomaly_count"], 0)
        self.assertIn("late_delivery_rate", anomalous["anomalous_metrics"])

        normals = result[result["seller_id"] == "s_normal"]
        self.assertFalse(normals["is_anomaly"].any())

    def test_detect_anomalies_includes_per_metric_flags(self):
        sellers = _make_sellers()
        result = detect_anomalies(sellers)

        self.assertIn("late_delivery_rate_iqr", result.columns)
        self.assertIn("late_delivery_rate_zscore", result.columns)
        self.assertIn("average_review_score_iqr", result.columns)

    def test_detect_anomalies_excludes_ineligible_sellers(self):
        sellers = _make_sellers()
        sellers.loc[sellers["seller_id"] == "s_anomalous", "eligible_for_risk_score"] = False
        result = detect_anomalies(sellers)

        self.assertEqual(len(result), 10)
        self.assertFalse(result["is_anomaly"].any())

    def test_build_anomaly_summary_counts_by_metric(self):
        sellers = _make_sellers()
        anomalies = detect_anomalies(sellers)
        summary = build_anomaly_summary(anomalies)

        self.assertIn("metric", summary.columns)
        self.assertIn("iqr_flagged", summary.columns)
        self.assertIn("zscore_flagged", summary.columns)
        self.assertEqual(len(summary), 5)
        total_flagged = summary["either_flagged"].sum()
        self.assertGreater(total_flagged, 0)


if __name__ == "__main__":
    unittest.main()
