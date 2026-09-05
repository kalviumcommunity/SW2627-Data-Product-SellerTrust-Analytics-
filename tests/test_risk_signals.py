import unittest

import pandas as pd

from src.risk_signals import decompose_risk_signals


def _make_seller(**overrides) -> pd.DataFrame:
    defaults = {
        "seller_id": ["s1"],
        "total_orders": [10],
        "late_delivery_rate": [0.0],
        "average_review_score": [5.0],
        "negative_review_rate": [0.0],
        "cancellation_rate_proxy": [0.0],
        "eligible_for_risk_score": [True],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


class RiskSignalDecompositionTests(unittest.TestCase):
    def test_perfect_seller_all_raw_scores_100(self):
        result = decompose_risk_signals(_make_seller())
        self.assertEqual(result.loc[0, "delivery_raw"], 100.0)
        self.assertEqual(result.loc[0, "review_raw"], 100.0)
        self.assertEqual(result.loc[0, "cancellation_raw"], 100.0)
        self.assertEqual(result.loc[0, "negative_review_raw"], 100.0)

    def test_perfect_seller_trust_score_100(self):
        result = decompose_risk_signals(_make_seller())
        self.assertEqual(result.loc[0, "trust_score"], 100.0)

    def test_worst_seller_all_raw_scores_0(self):
        result = decompose_risk_signals(
            _make_seller(
                late_delivery_rate=1.0,
                average_review_score=1.0,
                negative_review_rate=1.0,
                cancellation_rate_proxy=1.0,
            )
        )
        self.assertEqual(result.loc[0, "delivery_raw"], 0.0)
        self.assertEqual(result.loc[0, "review_raw"], 0.0)
        self.assertEqual(result.loc[0, "cancellation_raw"], 0.0)
        self.assertEqual(result.loc[0, "negative_review_raw"], 0.0)

    def test_contributions_sum_to_trust_score(self):
        result = decompose_risk_signals(_make_seller(late_delivery_rate=0.2, average_review_score=3.5))
        total_contribution = (
            result.loc[0, "delivery_contribution"]
            + result.loc[0, "review_contribution"]
            + result.loc[0, "cancellation_contribution"]
            + result.loc[0, "negative_review_contribution"]
        )
        self.assertAlmostEqual(result.loc[0, "trust_score"], total_contribution, places=1)

    def test_weakest_signal_identified(self):
        result = decompose_risk_signals(
            _make_seller(
                late_delivery_rate=0.8, average_review_score=5.0, negative_review_rate=0.0, cancellation_rate_proxy=0.0
            )
        )
        self.assertEqual(result.loc[0, "weakest_signal"], "delivery")

    def test_ineligible_sellers_get_nan(self):
        result = decompose_risk_signals(_make_seller(eligible_for_risk_score=False))
        self.assertTrue(pd.isna(result.loc[0, "trust_score"]))

    def test_output_contains_all_columns(self):
        result = decompose_risk_signals(_make_seller())
        expected_cols = [
            "seller_id",
            "trust_score",
            "delivery_raw",
            "review_raw",
            "cancellation_raw",
            "negative_review_raw",
            "delivery_contribution",
            "review_contribution",
            "cancellation_contribution",
            "negative_review_contribution",
            "weakest_signal",
        ]
        for col in expected_cols:
            self.assertIn(col, result.columns)

    def test_multiple_sellers(self):
        sellers = pd.concat(
            [
                _make_seller(seller_id="s1", late_delivery_rate=0.0),
                _make_seller(seller_id="s2", late_delivery_rate=0.9),
            ]
        ).reset_index(drop=True)
        result = decompose_risk_signals(sellers).reset_index(drop=True)
        self.assertEqual(len(result), 2)
        self.assertGreater(result.loc[0, "delivery_raw"], result.loc[1, "delivery_raw"])


if __name__ == "__main__":
    unittest.main()
