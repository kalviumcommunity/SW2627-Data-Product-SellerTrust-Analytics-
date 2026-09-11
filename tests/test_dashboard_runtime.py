import unittest
from pathlib import Path

import pandas as pd

from app.runtime import refresh_dashboard_data
from app.seller_detail import build_seller_detail, seller_detail_csv
from app.signals import load_seller_order_fact, prepare_signal_metrics


class DashboardRuntimeTests(unittest.TestCase):
    def test_dashboard_starts_without_streamlit_exception(self):
        from streamlit.testing.v1 import AppTest

        app_path = Path(__file__).resolve().parents[1] / "app" / "main.py"
        app = AppTest.from_file(app_path).run(timeout=30)
        self.assertFalse(app.exception, [str(error) for error in app.exception])
        self.assertIn("Seller Trust Analytics Dashboard", [title.value for title in app.title])

    def test_missing_database_returns_a_clear_error(self):
        with self.assertRaisesRegex(FileNotFoundError, "SQLite database not found"):
            load_seller_order_fact(db_path=Path("tmp-missing-dashboard.db"))

    def test_empty_seller_selection_returns_empty_facts(self):
        result = load_seller_order_fact([], db_path=Path("data/trust_analytics.db"))
        self.assertTrue(result.empty)

    def test_malformed_metrics_are_rejected_without_partial_results(self):
        malformed = pd.DataFrame(
            {
                "seller_id": ["seller-1"],
                "eligible_for_risk_score": [True],
                "trust_score": ["not-a-number"],
            }
        )
        result = prepare_signal_metrics(malformed)
        self.assertTrue(result.empty)

    def test_refresh_failure_is_returned_for_dashboard_display(self):
        def failing_pipeline(**_kwargs):
            raise OSError("raw files are unavailable")

        success, message = refresh_dashboard_data(failing_pipeline)
        self.assertFalse(success)
        self.assertEqual(message, "raw files are unavailable")

    def test_refresh_success_is_returned_for_dashboard_display(self):
        calls = []

        def successful_pipeline(**kwargs):
            calls.append(kwargs)

        success, message = refresh_dashboard_data(successful_pipeline)
        self.assertTrue(success)
        self.assertEqual(message, "Dashboard data refreshed successfully.")
        self.assertEqual(calls[0]["db_path"], "data/trust_analytics.db")

    def test_seller_detail_selection_and_download_include_selected_seller(self):
        metrics = pd.DataFrame(
            {
                "seller_id": ["seller-1"],
                "trust_score": [82.0],
                "risk_tier": ["Reliable"],
                "total_orders": [10],
                "eligible_for_risk_score": [True],
                "late_delivery_rate": [0.0],
                "average_review_score": [4.5],
                "negative_review_rate": [0.0],
                "cancellation_rate_proxy": [0.0],
                "average_response_time_hours": [1.0],
                "review_count": [10],
                "delivered_orders_with_dates": [10],
            }
        )
        fact = pd.DataFrame(
            columns=[
                "seller_id",
                "order_id",
                "review_score",
                "order_purchase_timestamp",
                "delivery_delay_days",
                "is_late_delivery",
                "order_status",
            ]
        )
        detail = build_seller_detail(metrics, fact, "seller-1")
        self.assertIn("seller-1", seller_detail_csv(detail).decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
