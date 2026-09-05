import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.pipeline import build_seller_metrics, build_seller_order_fact, profile_frame, run_pipeline


class PipelineTests(unittest.TestCase):
    def test_profile_reports_null_metrics(self):
        profile = profile_frame(pd.DataFrame({"value": [1, None]})).set_index("column")
        self.assertEqual(profile.loc["value", "null_count"], 1)
        self.assertEqual(profile.loc["value", "null_pct"], 50.0)

    def test_fact_prevents_multiple_items_from_double_counting_orders(self):
        cleaned = {
            "items": pd.DataFrame(
                {
                    "order_id": ["o1", "o1"],
                    "seller_id": ["s1", "s1"],
                    "product_id": ["p1", "p2"],
                    "price": [10, 20],
                    "freight_value": [2, 3],
                }
            ),
            "products": pd.DataFrame({"product_id": ["p1", "p2"], "product_category_name": ["books", "books"]}),
            "orders": pd.DataFrame(
                {
                    "order_id": ["o1"],
                    "order_status": ["delivered"],
                    "is_late_delivery": [False],
                    "delivery_delay_days": [-1],
                }
            ),
            "sellers": pd.DataFrame({"seller_id": ["s1"], "seller_city": ["x"], "seller_state": ["sp"]}),
            "reviews": pd.DataFrame(
                {
                    "review_id": ["r1"],
                    "order_id": ["o1"],
                    "review_score": [5],
                    "review_creation_date": ["2018-01-01"],
                    "review_answer_timestamp": ["2018-01-02"],
                }
            ),
        }
        fact = build_seller_order_fact(cleaned)
        self.assertEqual(len(fact), 1)
        self.assertEqual(fact.loc[0, "item_value"], 30)
        self.assertEqual(fact.loc[0, "item_count"], 2)

    def test_seller_metrics_use_unique_orders_and_locked_proxies(self):
        fact = pd.DataFrame(
            {
                "seller_id": ["s1"] * 5,
                "order_id": list("abcde"),
                "order_status": ["canceled", "delivered", "delivered", "delivered", "delivered"],
                "is_late_delivery": [True, False, False, False, False],
                "delivery_delay_days": [2, -1, -1, -1, -1],
                "review_score": [1, 2, 4, 5, 5],
                "response_time_hours": [1, 1, 1, 1, 1],
            }
        )
        metrics = build_seller_metrics(fact).iloc[0]
        self.assertEqual(metrics["total_orders"], 5)
        self.assertEqual(metrics["cancellation_rate_proxy"], 0.2)
        self.assertEqual(metrics["negative_review_rate"], 0.4)
        self.assertTrue(metrics["eligible_for_risk_score"])

    def test_pipeline_writes_dashboard_ready_outputs(self):
        with TemporaryDirectory() as temp_dir:
            raw = Path(temp_dir) / "raw"
            output = Path(temp_dir) / "processed"
            raw.mkdir()
            pd.DataFrame(
                {
                    "order_id": ["o1"],
                    "customer_id": ["c1"],
                    "order_status": ["delivered"],
                    "order_purchase_timestamp": ["2018-01-01"],
                    "order_approved_at": ["2018-01-01"],
                    "order_delivered_carrier_date": ["2018-01-02"],
                    "order_delivered_customer_date": ["2018-01-03"],
                    "order_estimated_delivery_date": ["2018-01-04"],
                }
            ).to_csv(raw / "olist_orders_dataset.csv", index=False)
            pd.DataFrame(
                {"order_id": ["o1"], "product_id": ["p1"], "seller_id": ["s1"], "price": [10], "freight_value": [2]}
            ).to_csv(raw / "olist_order_items_dataset.csv", index=False)
            pd.DataFrame(
                {
                    "review_id": ["r1"],
                    "order_id": ["o1"],
                    "review_score": [5],
                    "review_creation_date": ["2018-01-04"],
                    "review_answer_timestamp": ["2018-01-05"],
                }
            ).to_csv(raw / "olist_order_reviews_dataset.csv", index=False)
            pd.DataFrame({"seller_id": ["s1"], "seller_city": ["Sao Paulo"], "seller_state": ["SP"]}).to_csv(
                raw / "olist_sellers_dataset.csv", index=False
            )
            pd.DataFrame({"product_id": ["p1"], "product_category_name": ["Books"]}).to_csv(
                raw / "olist_products_dataset.csv", index=False
            )

            result = run_pipeline(raw, output)
            self.assertEqual(len(result["seller_metrics"]), 1)
            self.assertTrue((output / "seller_order_fact.csv").exists())
            self.assertTrue((output / "seller_metrics.csv").exists())
