"""Tests for wiring sql/views.sql into the SQLite loader.

The views file existed for several releases but nothing ever executed it, so the
database shipped with zero views. These tests pin the wiring so it cannot rot back.
"""

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.sql_loader import DEFAULT_VIEWS_PATH, apply_views, load_to_sql, view_names

EXPECTED_VIEWS = ["vw_seller_trust_metrics", "vw_category_risk", "vw_monthly_trends"]


def write_processed_csvs(directory: Path) -> None:
    """Minimal seller_order_fact and seller_metrics the views can be built over."""
    directory.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3"],
            "seller_id": ["s1", "s1", "s2"],
            "item_count": [1, 2, 1],
            "item_value": [10.0, 20.0, 30.0],
            "freight_value": [1.0, 2.0, 3.0],
            "product_category_name": ["books", "books", None],
            "order_status": ["delivered", "delivered", "canceled"],
            "order_purchase_timestamp": ["2018-01-01", "2018-02-01", "2018-02-15"],
            "delivery_delay_days": [-1.0, 2.0, None],
            "is_late_delivery": [0, 1, 0],
            "purchase_month": ["2018-01", "2018-02", "2018-02"],
            "review_score": [5.0, 2.0, 1.0],
            "review_count": [1.0, 1.0, 1.0],
            "response_time_hours": [4.0, 8.0, 2.0],
            "sentiment_bucket": ["positive", "negative", "negative"],
        }
    ).to_csv(directory / "seller_order_fact.csv", index=False)

    pd.DataFrame(
        {
            "seller_id": ["s1", "s2"],
            "total_orders": [7, 1],
            "cancelled_orders": [0, 1],
            "late_delivery_rate": [0.5, 0.0],
            "average_delivery_delay_days": [0.5, None],
            "average_review_score": [3.5, 1.0],
            "negative_review_rate": [0.5, 1.0],
            "average_response_time_hours": [6.0, 2.0],
            "cancellation_rate_proxy": [0.0, 1.0],
            "eligible_for_risk_score": [1, 0],
        }
    ).to_csv(directory / "seller_metrics.csv", index=False)


class ViewNameTests(unittest.TestCase):
    def test_view_names_are_parsed_from_the_sql_file(self):
        self.assertEqual(view_names(), EXPECTED_VIEWS)

    def test_the_shipped_sql_file_is_where_the_loader_expects(self):
        self.assertTrue(Path(DEFAULT_VIEWS_PATH).is_file())


class ApplyViewsTests(unittest.TestCase):
    def _loaded_db(self, temp_dir: str) -> Path:
        processed = Path(temp_dir) / "processed"
        write_processed_csvs(processed)
        db_path = Path(temp_dir) / "analytics.db"
        load_to_sql(processed, db_path)
        return db_path

    @staticmethod
    def _views_in(db_path: Path) -> list[str]:
        conn = sqlite3.connect(str(db_path))
        try:
            return [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")]
        finally:
            conn.close()

    def test_load_to_sql_creates_the_views(self):
        """The regression this whole file exists for: loading data used to leave 0 views."""
        with TemporaryDirectory() as temp_dir:
            db_path = self._loaded_db(temp_dir)
            self.assertCountEqual(self._views_in(db_path), EXPECTED_VIEWS)

    def test_every_view_is_queryable(self):
        with TemporaryDirectory() as temp_dir:
            db_path = self._loaded_db(temp_dir)
            conn = sqlite3.connect(str(db_path))
            try:
                for view in EXPECTED_VIEWS:
                    rows = conn.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
                    self.assertGreater(rows, 0, f"{view} returned no rows")
            finally:
                conn.close()

    def test_applying_twice_succeeds(self):
        """views.sql uses bare CREATE VIEW, so a re-run only works because we drop first."""
        with TemporaryDirectory() as temp_dir:
            db_path = self._loaded_db(temp_dir)
            apply_views(db_path)
            apply_views(db_path)
            self.assertCountEqual(self._views_in(db_path), EXPECTED_VIEWS)

    def test_views_survive_a_data_reload(self):
        """to_sql(if_exists='replace') drops the tables underneath the views."""
        with TemporaryDirectory() as temp_dir:
            processed = Path(temp_dir) / "processed"
            write_processed_csvs(processed)
            db_path = Path(temp_dir) / "analytics.db"
            load_to_sql(processed, db_path)
            load_to_sql(processed, db_path)
            conn = sqlite3.connect(str(db_path))
            try:
                self.assertGreater(conn.execute("SELECT COUNT(*) FROM vw_seller_trust_metrics").fetchone()[0], 0)
            finally:
                conn.close()

    def test_views_can_be_skipped(self):
        with TemporaryDirectory() as temp_dir:
            processed = Path(temp_dir) / "processed"
            write_processed_csvs(processed)
            db_path = Path(temp_dir) / "analytics.db"
            load_to_sql(processed, db_path, views_path=None)
            self.assertEqual(self._views_in(db_path), [])

    def test_missing_sql_file_raises(self):
        with TemporaryDirectory() as temp_dir:
            db_path = self._loaded_db(temp_dir)
            with self.assertRaises(FileNotFoundError):
                apply_views(db_path, Path(temp_dir) / "nope.sql")


class ViewContentTests(unittest.TestCase):
    def test_seller_view_uses_the_canonical_risk_tier(self):
        """The SQL view uses the same seller risk-tier vocabulary as Python."""
        with TemporaryDirectory() as temp_dir:
            processed = Path(temp_dir) / "processed"
            write_processed_csvs(processed)
            db_path = Path(temp_dir) / "analytics.db"
            load_to_sql(processed, db_path)
            conn = sqlite3.connect(str(db_path))
            try:
                columns = [row[1] for row in conn.execute("PRAGMA table_info(vw_seller_trust_metrics)")]
            finally:
                conn.close()
            self.assertIn("risk_tier", columns)
            self.assertNotIn("trust_score_band", columns)

    def test_ineligible_sellers_have_no_trust_score_in_the_view(self):
        with TemporaryDirectory() as temp_dir:
            processed = Path(temp_dir) / "processed"
            write_processed_csvs(processed)
            db_path = Path(temp_dir) / "analytics.db"
            load_to_sql(processed, db_path)
            conn = sqlite3.connect(str(db_path))
            try:
                row = conn.execute(
                    "SELECT trust_score, risk_tier FROM vw_seller_trust_metrics WHERE seller_id = 's2'"
                ).fetchone()
            finally:
                conn.close()
            self.assertIsNone(row[0])
            self.assertEqual(row[1], "Insufficient Data")


if __name__ == "__main__":
    unittest.main()
