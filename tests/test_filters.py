import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from app.filters import assign_risk_tier, get_category_options, query_seller_metrics


class SidebarFilterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "trust_analytics.db"
        conn = sqlite3.connect(self.db_path)
        pd.DataFrame(
            {
                "seller_id": ["seller_a", "seller_b", "seller_c"],
                "total_orders": [10, 8, 7],
                "cancelled_orders": [0, 2, 5],
                "late_delivery_rate": [0.0, 0.4, 0.9],
                "average_delivery_delay_days": [0.0, 2.0, 7.0],
                "average_review_score": [5.0, 3.0, 1.5],
                "negative_review_rate": [0.0, 0.4, 0.8],
                "average_response_time_hours": [12.0, 24.0, 48.0],
                "cancellation_rate_proxy": [0.0, 0.25, 0.7],
                "eligible_for_risk_score": [True, True, True],
            }
        ).to_sql("seller_metrics", conn, index=False)
        pd.DataFrame(
            {
                "order_id": ["o1", "o2", "o3"],
                "seller_id": ["seller_a", "seller_b", "seller_c"],
                "product_category_name": ["books", "electronics", "books"],
            }
        ).to_sql("seller_order_fact", conn, index=False)
        conn.close()

    def tearDown(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def test_category_options_are_loaded_from_sqlite(self):
        self.assertEqual(
            get_category_options(self.db_path),
            ["All", "books", "electronics"],
        )

    def test_query_filters_by_seller_search(self):
        result = query_seller_metrics("seller_b", db_path=self.db_path)
        self.assertEqual(result["seller_id"].tolist(), ["seller_b"])

    def test_query_filters_by_category(self):
        result = query_seller_metrics(category="electronics", db_path=self.db_path)
        self.assertEqual(result["seller_id"].tolist(), ["seller_b"])

    def test_query_filters_by_risk_tier(self):
        result = query_seller_metrics(risk_tier="High-Risk", db_path=self.db_path)
        self.assertEqual(result["seller_id"].tolist(), ["seller_c"])

    def test_assign_risk_tier_labels_scores(self):
        metrics = pd.DataFrame(
            {
                "seller_id": ["seller_a"],
                "total_orders": [10],
                "late_delivery_rate": [0.0],
                "average_review_score": [5.0],
                "negative_review_rate": [0.0],
                "cancellation_rate_proxy": [0.0],
                "eligible_for_risk_score": [True],
            }
        )
        result = assign_risk_tier(metrics)
        self.assertEqual(result.loc[0, "risk_tier"], "Reliable")


if __name__ == "__main__":
    unittest.main()
