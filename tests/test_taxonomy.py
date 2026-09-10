import unittest

import pandas as pd

from src.actions import recommend_actions
from src.taxonomy import INSUFFICIENT_DATA, add_canonical_risk_tier, risk_tier_for_score


class RiskTaxonomyTests(unittest.TestCase):
    def test_score_boundaries_use_canonical_labels(self):
        expected = {
            45: "High-Risk",
            60: "Return-Prone",
            75: "Inconsistent",
            100: "Reliable",
        }
        for score, label in expected.items():
            self.assertEqual(risk_tier_for_score(score), label)

    def test_missing_score_is_insufficient_data(self):
        self.assertEqual(risk_tier_for_score(pd.NA), INSUFFICIENT_DATA)

    def test_add_canonical_risk_tier_replaces_stale_labels(self):
        metrics = pd.DataFrame(
            {
                "trust_score": [40.0, 70.0, pd.NA],
                "risk_tier": ["ESCALATE", "MONITOR", "COACH"],
            }
        )
        result = add_canonical_risk_tier(metrics)
        self.assertEqual(result["risk_tier"].tolist(), ["High-Risk", "Inconsistent", INSUFFICIENT_DATA])

    def test_actions_preserve_canonical_risk_tier_and_separate_action(self):
        metrics = pd.DataFrame(
            {
                "seller_id": ["s1"],
                "total_orders": [10],
                "late_delivery_rate": [0.8],
                "average_review_score": [1.5],
                "negative_review_rate": [0.9],
                "cancellation_rate_proxy": [0.3],
                "average_response_time_hours": [50.0],
                "eligible_for_risk_score": [True],
            }
        )
        result = recommend_actions(metrics)
        self.assertEqual(result.loc[0, "risk_tier"], "High-Risk")
        self.assertEqual(result.loc[0, "recommended_action"], "Escalate")


if __name__ == "__main__":
    unittest.main()
