import unittest

import pandas as pd

from app.category import build_category_analysis, category_analysis_csv


class CategoryAnalysisTests(unittest.TestCase):
    def test_rollup_uses_unique_seller_contributions_and_warns_small_samples(self):
        metrics = pd.DataFrame(
            {
                "seller_id": ["s1", "s2"],
                "trust_score": [80.0, 60.0],
                "risk_tier": ["Reliable", "Return-Prone"],
            }
        )
        fact = pd.DataFrame(
            {
                "seller_id": ["s1", "s1", "s2"],
                "order_id": ["o1", "o2", "o3"],
                "product_category_name": ["books", "books", "books"],
                "order_status": ["delivered", "canceled", "delivered"],
                "is_late_delivery": [0, pd.NA, 1],
                "review_score": [5.0, 4.0, 2.0],
            }
        )
        result = build_category_analysis(metrics, fact)
        row = result.iloc[0]
        self.assertEqual(row["unique_sellers"], 2)
        self.assertEqual(row["total_orders"], 3)
        self.assertEqual(row["avg_trust_score"], 70.0)
        self.assertTrue(row["sample_warning"])
        self.assertIn("Late delivery", row["top_trust_eroding_behaviours"])
        self.assertIn(b"category", category_analysis_csv(result))


if __name__ == "__main__":
    unittest.main()
