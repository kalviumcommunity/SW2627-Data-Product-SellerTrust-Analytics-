import unittest

import pandas as pd

from src.thresholds import (
    RISK_METRICS,
    build_threshold_config,
    compute_percentile_ranks,
    derive_percentile_cutoffs,
)


def _sample_metrics() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "seller_id": ["s1", "s2", "s3", "s4"],
            "late_delivery_rate": [0.1, 0.2, 0.3, 0.4],
            "average_review_score": [2.0, 3.0, 4.0, 5.0],
            "cancellation_rate_proxy": [0.05, 0.10, 0.15, 0.20],
            "negative_review_rate": [0.4, 0.3, 0.2, 0.1],
        }
    )


class ThresholdTests(unittest.TestCase):
    def test_compute_percentile_ranks_returns_expected_columns(self):
        ranks = compute_percentile_ranks(_sample_metrics())
        expected = {f"{metric}_percentile" for metric in RISK_METRICS}
        self.assertEqual(set(ranks.columns), expected)

    def test_compute_percentile_ranks_values_are_empirical(self):
        ranks = compute_percentile_ranks(_sample_metrics())
        self.assertAlmostEqual(ranks.loc[0, "late_delivery_rate_percentile"], 0.25)
        self.assertAlmostEqual(ranks.loc[3, "late_delivery_rate_percentile"], 1.0)

    def test_derive_percentile_cutoffs_from_data(self):
        cutoffs = derive_percentile_cutoffs(_sample_metrics(), percentiles=[0.5, 0.75])
        self.assertAlmostEqual(cutoffs["late_delivery_rate"]["0.5"], 0.25)
        self.assertAlmostEqual(cutoffs["late_delivery_rate"]["0.75"], 0.325)

    def test_build_threshold_config_is_trust_score_consumable(self):
        config = build_threshold_config(_sample_metrics(), percentiles=[0.5, 0.9])
        self.assertEqual(config["strategy"], "percentile")
        self.assertEqual(config["metric_columns"], list(RISK_METRICS))
        self.assertEqual(config["percentiles"], [0.5, 0.9])
        self.assertIn("late_delivery_rate", config["cutoffs"])

    def test_invalid_percentile_raises_value_error(self):
        with self.assertRaises(ValueError):
            derive_percentile_cutoffs(_sample_metrics(), percentiles=[1.2])


if __name__ == "__main__":
    unittest.main()
