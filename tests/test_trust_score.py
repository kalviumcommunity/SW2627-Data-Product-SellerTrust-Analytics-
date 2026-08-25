import unittest

import pandas as pd

from src.trust_score import WEIGHTS, calculate_trust_score


def _make_seller(**overrides) -> pd.DataFrame:
    defaults = {
        "seller_id": ["s1"],
        "total_orders": [10],
        "late_delivery_rate": [0.0],
        "average_review_score": [4.0],
        "negative_review_rate": [0.0],
        "cancellation_rate_proxy": [0.0],
        "eligible_for_risk_score": [True],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


class TrustScoreTests(unittest.TestCase):
    def test_perfect_seller_scores_100(self):
        perfect = _make_seller(
            late_delivery_rate=0.0,
            average_review_score=5.0,
            negative_review_rate=0.0,
            cancellation_rate_proxy=0.0,
        )
        result = calculate_trust_score(perfect)
        self.assertAlmostEqual(result.loc[0, "trust_score"], 100.0)

    def test_worst_seller_scores_0(self):
        worst = _make_seller(
            late_delivery_rate=1.0,
            average_review_score=1.0,
            negative_review_rate=1.0,
            cancellation_rate_proxy=1.0,
        )
        result = calculate_trust_score(worst)
        self.assertAlmostEqual(result.loc[0, "trust_score"], 0.0)

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0)

    def test_ineligible_sellers_get_nan(self):
        seller = _make_seller(eligible_for_risk_score=False)
        result = calculate_trust_score(seller)
        self.assertTrue(pd.isna(result.loc[0, "trust_score"]))

    def test_score_is_between_0_and_100(self):
        seller = _make_seller(
            late_delivery_rate=0.5,
            average_review_score=3.0,
            negative_review_rate=0.3,
            cancellation_rate_proxy=0.1,
        )
        result = calculate_trust_score(seller)
        score = result.loc[0, "trust_score"]
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_output_contains_all_input_columns(self):
        seller = _make_seller()
        result = calculate_trust_score(seller)
        self.assertIn("trust_score", result.columns)
        self.assertIn("seller_id", result.columns)
        self.assertIn("total_orders", result.columns)

    def test_multiple_sellers_scored_independently(self):
        sellers = pd.DataFrame(
            {
                "seller_id": ["s1", "s2"],
                "total_orders": [10, 10],
                "late_delivery_rate": [0.0, 1.0],
                "average_review_score": [5.0, 1.0],
                "negative_review_rate": [0.0, 1.0],
                "cancellation_rate_proxy": [0.0, 1.0],
                "eligible_for_risk_score": [True, True],
            }
        )
        result = calculate_trust_score(sellers)
        self.assertEqual(result.loc[0, "trust_score"], 100.0)
        self.assertEqual(result.loc[1, "trust_score"], 0.0)

    def test_missing_review_score_produces_nan_component(self):
        seller = _make_seller(average_review_score=pd.NA)
        result = calculate_trust_score(seller)
        self.assertTrue(pd.isna(result.loc[0, "trust_score"]))


if __name__ == "__main__":
    unittest.main()
