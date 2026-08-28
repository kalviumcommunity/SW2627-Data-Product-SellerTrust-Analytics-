import unittest

import pandas as pd

from app.overview import build_overview_kpis, prepare_seller_metrics


class OverviewKpiTests(unittest.TestCase):
    def test_build_overview_kpis_summarises_eligible_sellers(self):
        metrics = pd.DataFrame(
            {
                "seller_id": ["s1", "s2", "s3"],
                "total_orders": [10, 20, 1],
                "late_delivery_rate": [0.0, 1.0, 0.0],
                "average_review_score": [5.0, 1.0, 5.0],
                "negative_review_rate": [0.0, 1.0, 0.0],
                "cancellation_rate_proxy": [0.0, 1.0, 0.0],
                "eligible_for_risk_score": [True, True, False],
            }
        )

        overview = build_overview_kpis(metrics)

        self.assertEqual(overview["avg_trust_score"], 50.0)
        self.assertEqual(overview["return_rate_pct"], 50.0)
        self.assertEqual(overview["negative_sentiment_pct"], 50.0)
        self.assertEqual(overview["at_risk_sellers_count"], 1)

    def test_prepare_seller_metrics_keeps_existing_trust_score(self):
        metrics = pd.DataFrame(
            {
                "seller_id": ["s1"],
                "trust_score": [72.5],
                "eligible_for_risk_score": [True],
            }
        )

        prepared = prepare_seller_metrics(metrics)

        self.assertEqual(prepared.loc[0, "trust_score"], 72.5)


if __name__ == "__main__":
    unittest.main()
