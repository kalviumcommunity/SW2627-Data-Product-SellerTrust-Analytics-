import unittest

import pandas as pd

from app.actions import build_action_cards, format_evidence_bullets


class ActionCardTests(unittest.TestCase):
    def test_build_action_cards_includes_flagged_sellers_only(self):
        metrics = pd.DataFrame(
            {
                "seller_id": ["good_seller", "bad_seller", "watch_seller"],
                "total_orders": [20, 20, 20],
                "late_delivery_rate": [0.0, 0.9, 0.2],
                "average_review_score": [5.0, 1.0, 3.2],
                "negative_review_rate": [0.0, 0.95, 0.1],
                "average_response_time_hours": [8.0, 150.0, 30.0],
                "cancellation_rate_proxy": [0.0, 0.5, 0.01],
                "eligible_for_risk_score": [True, True, True],
            }
        )

        cards = build_action_cards(metrics)

        self.assertNotIn("good_seller", cards["seller_id"].tolist())
        self.assertIn("bad_seller", cards["seller_id"].tolist())
        self.assertIn("watch_seller", cards["seller_id"].tolist())
        self.assertIn("action_badge", cards.columns)
        self.assertIn("severity_color", cards.columns)
        self.assertIn("severity_label", cards.columns)

    def test_escalate_card_gets_high_severity_indicator(self):
        metrics = pd.DataFrame(
            {
                "seller_id": ["bad_seller"],
                "total_orders": [20],
                "late_delivery_rate": [0.9],
                "average_review_score": [1.0],
                "negative_review_rate": [0.95],
                "average_response_time_hours": [150.0],
                "cancellation_rate_proxy": [0.5],
                "eligible_for_risk_score": [True],
            }
        )

        card = build_action_cards(metrics).iloc[0]

        self.assertEqual(card["recommended_action"], "Escalate")
        self.assertEqual(card["severity_label"], "High Severity")
        self.assertIn("Escalate", card["action_badge"])

    def test_format_evidence_bullets_accepts_lists_and_pipe_strings(self):
        self.assertEqual(
            format_evidence_bullets(["Late deliveries", "Bad reviews"]),
            ["Late deliveries", "Bad reviews"],
        )
        self.assertEqual(
            format_evidence_bullets("Late deliveries | Bad reviews"),
            ["Late deliveries", "Bad reviews"],
        )


if __name__ == "__main__":
    unittest.main()
