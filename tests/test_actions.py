import unittest

import pandas as pd

from src.actions import (
    ACTION_COACH,
    ACTION_ESCALATE,
    ACTION_MONITOR,
    ACTION_NONE,
    _assign_action,
    _build_evidence,
    recommend_actions,
)


def _make_seller(**overrides) -> pd.DataFrame:
    defaults = {
        "seller_id": ["s1"],
        "total_orders": [10],
        "late_delivery_rate": [0.0],
        "average_review_score": [4.0],
        "negative_review_rate": [0.1],
        "cancellation_rate_proxy": [0.01],
        "average_response_time_hours": [50.0],
        "eligible_for_risk_score": [True],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


class ActionRecommendationTests(unittest.TestCase):
    def test_escalate_for_very_low_trust_score(self):
        action = _assign_action(trust_score=30.0, anomaly_count=1, negative_review_rate=0.5, cancellation_rate=0.1)
        self.assertEqual(action, ACTION_ESCALATE)

    def test_escalate_for_medium_score_with_many_anomalies(self):
        action = _assign_action(trust_score=55.0, anomaly_count=3, negative_review_rate=0.1, cancellation_rate=0.01)
        self.assertEqual(action, ACTION_ESCALATE)

    def test_coach_for_medium_trust_score(self):
        action = _assign_action(trust_score=55.0, anomaly_count=1, negative_review_rate=0.1, cancellation_rate=0.01)
        self.assertEqual(action, ACTION_COACH)

    def test_coach_for_high_negative_review_rate(self):
        action = _assign_action(trust_score=75.0, anomaly_count=0, negative_review_rate=0.3, cancellation_rate=0.01)
        self.assertEqual(action, ACTION_COACH)

    def test_monitor_for_borderline_score(self):
        action = _assign_action(trust_score=75.0, anomaly_count=0, negative_review_rate=0.1, cancellation_rate=0.01)
        self.assertEqual(action, ACTION_MONITOR)

    def test_no_action_for_high_trust_score(self):
        action = _assign_action(trust_score=90.0, anomaly_count=0, negative_review_rate=0.05, cancellation_rate=0.0)
        self.assertEqual(action, ACTION_NONE)

    def test_monitor_for_nan_score(self):
        action = _assign_action(trust_score=None, anomaly_count=0, negative_review_rate=0.0, cancellation_rate=0.0)
        self.assertEqual(action, ACTION_MONITOR)

    def test_evidence_includes_high_late_delivery(self):
        row = pd.Series(
            {
                "late_delivery_rate": 0.25,
                "average_review_score": 4.0,
                "negative_review_rate": 0.1,
                "cancellation_rate_proxy": 0.01,
                "average_response_time_hours": 50,
                "anomaly_count": 0,
            }
        )
        evidence = _build_evidence(row)
        self.assertTrue(any("Late delivery" in e for e in evidence))

    def test_evidence_includes_low_review_score(self):
        row = pd.Series(
            {
                "late_delivery_rate": 0.0,
                "average_review_score": 2.5,
                "negative_review_rate": 0.1,
                "cancellation_rate_proxy": 0.01,
                "average_response_time_hours": 50,
                "anomaly_count": 0,
            }
        )
        evidence = _build_evidence(row)
        self.assertTrue(any("review score" in e for e in evidence))

    def test_evidence_includes_anomaly_count(self):
        row = pd.Series(
            {
                "late_delivery_rate": 0.0,
                "average_review_score": 4.0,
                "negative_review_rate": 0.1,
                "cancellation_rate_proxy": 0.01,
                "average_response_time_hours": 50,
                "anomaly_count": 4,
            }
        )
        evidence = _build_evidence(row)
        self.assertTrue(any("metrics flagged as anomalous" in e for e in evidence))

    def test_evidence_clean_seller(self):
        row = pd.Series(
            {
                "late_delivery_rate": 0.01,
                "average_review_score": 4.5,
                "negative_review_rate": 0.02,
                "cancellation_rate_proxy": 0.0,
                "average_response_time_hours": 40,
                "anomaly_count": 0,
            }
        )
        evidence = _build_evidence(row)
        self.assertTrue(any("No significant" in e for e in evidence))

    def test_recommend_actions_returns_all_columns(self):
        sellers = pd.concat(
            [
                _make_seller(seller_id="s1"),
                _make_seller(
                    seller_id="s2",
                    late_delivery_rate=0.8,
                    average_review_score=1.5,
                    negative_review_rate=0.9,
                    cancellation_rate_proxy=0.3,
                ),
            ]
        )
        result = recommend_actions(sellers)
        self.assertIn("seller_id", result.columns)
        self.assertIn("trust_score", result.columns)
        self.assertIn("risk_tier", result.columns)
        self.assertIn("recommended_action", result.columns)
        self.assertIn("evidence", result.columns)
        self.assertIn("anomaly_count", result.columns)

    def test_recommend_actions_bad_seller_gets_escalate(self):
        bad = _make_seller(
            seller_id="s_bad",
            late_delivery_rate=0.9,
            average_review_score=1.0,
            negative_review_rate=0.95,
            cancellation_rate_proxy=0.4,
        )
        result = recommend_actions(bad)
        self.assertEqual(result.loc[0, "recommended_action"], ACTION_ESCALATE)

    def test_recommend_actions_good_seller_gets_no_action(self):
        good = _make_seller(
            seller_id="s_good",
            late_delivery_rate=0.0,
            average_review_score=5.0,
            negative_review_rate=0.0,
            cancellation_rate_proxy=0.0,
        )
        result = recommend_actions(good)
        self.assertEqual(result.loc[0, "recommended_action"], ACTION_NONE)

    def test_recommend_actions_ineligible_seller_gets_monitor(self):
        ineligible = _make_seller(seller_id="s_new", eligible_for_risk_score=False)
        result = recommend_actions(ineligible)
        self.assertEqual(result.loc[0, "recommended_action"], ACTION_MONITOR)


if __name__ == "__main__":
    unittest.main()
