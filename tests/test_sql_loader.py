import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.sql_loader import create_tables, get_connection, load_to_sql


class SQLLoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.data_dir = Path(self.tmp.name) / "processed"
        self.db_path = Path(self.tmp.name) / "test.db"
        self.data_dir.mkdir()

        pd.DataFrame(
            {
                "order_id": ["o1", "o2"],
                "seller_id": ["s1", "s2"],
                "item_count": [1, 2],
                "item_value": [10.0, 20.0],
                "freight_value": [2.0, 3.0],
                "product_category_name": ["books", "electronics"],
                "customer_id": ["c1", "c2"],
                "order_status": ["delivered", "canceled"],
                "order_purchase_timestamp": ["2018-01-01", "2018-01-02"],
                "order_approved_at": ["2018-01-01", "2018-01-02"],
                "order_delivered_carrier_date": ["2018-01-02", None],
                "order_delivered_customer_date": ["2018-01-03", None],
                "order_estimated_delivery_date": ["2018-01-04", "2018-01-05"],
                "delivery_delay_days": [-1.0, None],
                "is_late_delivery": [False, None],
                "order_age_days": [3.0, 3.0],
                "purchase_month": ["2018-01", "2018-01"],
                "seller_zip_code_prefix": [12345, 67890],
                "seller_city": ["sp", "rj"],
                "seller_state": ["sp", "rj"],
                "review_score": [5.0, 1.0],
                "review_count": [1.0, 1.0],
                "response_time_hours": [24.0, 48.0],
                "sentiment_bucket": ["positive", "negative"],
            }
        ).to_csv(self.data_dir / "seller_order_fact.csv", index=False)

        pd.DataFrame(
            {
                "seller_id": ["s1", "s2"],
                "total_orders": [10, 5],
                "cancelled_orders": [0, 1],
                "late_delivery_rate": [0.0, 0.2],
                "average_delivery_delay_days": [-1.0, 2.0],
                "average_review_score": [4.5, 2.0],
                "negative_review_rate": [0.0, 0.4],
                "average_response_time_hours": [24.0, 48.0],
                "cancellation_rate_proxy": [0.0, 0.2],
                "eligible_for_risk_score": [True, True],
            }
        ).to_csv(self.data_dir / "seller_metrics.csv", index=False)

    def tearDown(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def test_create_tables_creates_db_file(self):
        create_tables(self.db_path)
        self.assertTrue(self.db_path.is_file())

    def test_load_to_sql_returns_row_counts(self):
        counts = load_to_sql(self.data_dir, self.db_path)
        self.assertEqual(counts["seller_order_fact"], 2)
        self.assertEqual(counts["seller_metrics"], 2)

    def test_loaded_data_is_queryable(self):
        load_to_sql(self.data_dir, self.db_path)
        conn = get_connection(self.db_path)
        result = conn.execute("SELECT COUNT(*) FROM seller_order_fact").fetchone()
        self.assertEqual(result[0], 2)
        result = conn.execute("SELECT COUNT(*) FROM seller_metrics").fetchone()
        self.assertEqual(result[0], 2)
        conn.close()

    def test_indexes_are_created(self):
        load_to_sql(self.data_dir, self.db_path)
        conn = get_connection(self.db_path)
        indexes = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        index_names = {row[0] for row in indexes}
        self.assertIn("idx_fact_seller", index_names)
        self.assertIn("idx_fact_order", index_names)
        self.assertIn("idx_metrics_seller", index_names)
        conn.close()

    def test_missing_csv_raises_file_not_found(self):
        empty_dir = Path(self.tmp.name) / "empty"
        empty_dir.mkdir()
        with self.assertRaises(FileNotFoundError):
            load_to_sql(empty_dir, self.db_path)

    def test_load_to_sql_replaces_existing_data(self):
        load_to_sql(self.data_dir, self.db_path)
        load_to_sql(self.data_dir, self.db_path)
        conn = get_connection(self.db_path)
        result = conn.execute("SELECT COUNT(*) FROM seller_order_fact").fetchone()
        self.assertEqual(result[0], 2)
        conn.close()


if __name__ == "__main__":
    unittest.main()
