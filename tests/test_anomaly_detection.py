import unittest

import pandas as pd

from src.anomaly_detection import (
    compute_seller_anomalies,
    detect_iqr_outliers,
    detect_zscore_anomalies,
)


_N_NORMAL = 19  # 19 normal + 1 anomalous gives Z≈4.4 at threshold=3.5


def _make_sellers() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "seller_id": ["s_normal"] * _N_NORMAL + ["s_anomalous"],
            "total_orders": [10] * _N_NORMAL + [8],
            "late_delivery_rate": [0.05] * _N_NORMAL + [0.9],
            "average_review_score": [4.0] * _N_NORMAL + [1.2],
            "negative_review_rate": [0.1] * _N_NORMAL + [0.95],
            "cancellation_rate_proxy": [0.01] * _N_NORMAL + [0.4],
            "average_response_time_hours": [60.0] * _N_NORMAL + [1200.0],
            "eligible_for_risk_score": [True] * (_N_NORMAL + 1),
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

    def test_min_orders_suppresses_zscore_for_low_volume_sellers(self):
        """Sellers below min_orders should not be Z-score flagged."""
        df = pd.DataFrame(
            {
                "seller_id": ["low_vol", "high_vol"],
                "total_orders": [2, 100],
                # Extreme late_delivery_rate would normally trigger Z-score
                "late_delivery_rate": [0.99, 0.05],
            }
        )
        result = compute_seller_anomalies(
            df,
            metrics=["late_delivery_rate"],
            min_orders=5,
            zscore_threshold=2.0,
        )
        low = result[result["seller_id"] == "low_vol"].iloc[0]
        # IQR may still flag it; Z-score specifically should be suppressed
        self.assertFalse(low["late_delivery_rate_zscore_anomaly"])

    def test_min_orders_zero_disables_filter(self):
        """Setting min_orders=0 should not suppress any Z-score flags."""
        df = pd.DataFrame(
            {
                "seller_id": ["low_vol"] * 5 + ["extreme"],
                "total_orders": [1] * 5 + [1],
                "late_delivery_rate": [0.05] * 5 + [0.99],
            }
        )
        result = compute_seller_anomalies(
            df,
            metrics=["late_delivery_rate"],
            min_orders=0,
            zscore_threshold=2.0,
        )
        extreme = result[result["seller_id"] == "extreme"].iloc[0]
        self.assertTrue(extreme["late_delivery_rate_zscore_anomaly"])

    def test_exclude_early_deliveries_suppresses_negative_delay_flags(self):
        """Negative delivery delay (early) should not be flagged when exclude_early_deliveries=True."""
        df = pd.DataFrame(
            {
                "seller_id": ["early"] * 5 + ["normal"] * 5,
                "total_orders": [20] * 10,
                # Heavily negative delay (very early delivery) — statistically extreme
                "average_delivery_delay_days": [-30.0] + [-1.0] * 4 + [1.0] * 5,
            }
        )
        result_excluded = compute_seller_anomalies(
            df,
            metrics=["average_delivery_delay_days"],
            exclude_early_deliveries=True,
            zscore_threshold=2.0,
        )
        early_row = result_excluded[result_excluded["seller_id"] == "early"].iloc[0]
        self.assertFalse(early_row["average_delivery_delay_days_anomaly"])

    def test_exclude_early_deliveries_false_allows_negative_delay_flags(self):
        """With exclude_early_deliveries=False, negative delays can still be flagged."""
        df = pd.DataFrame(
            {
                "seller_id": ["early"] + ["normal"] * 9,
                "total_orders": [20] * 10,
                "average_delivery_delay_days": [-30.0] + [1.0] * 9,
            }
        )
        result = compute_seller_anomalies(
            df,
            metrics=["average_delivery_delay_days"],
            exclude_early_deliveries=False,
            zscore_threshold=2.0,
        )
        early_row = result[result["seller_id"] == "early"].iloc[0]
        self.assertTrue(early_row["average_delivery_delay_days_anomaly"])

    def test_default_zscore_threshold_is_3_5(self):
        """Default threshold should be 3.5 (raised from 3.0 per validation docs)."""
        import inspect
        sig = inspect.signature(detect_zscore_anomalies)
        self.assertEqual(sig.parameters["threshold"].default, 3.5)


if __name__ == "__main__":
    unittest.main()
