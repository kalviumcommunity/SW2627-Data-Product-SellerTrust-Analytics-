import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.data_export import (
    export_seller_report,
    export_filtered_report,
    full_refresh,
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


def _write_sample_raw_files(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "order_id": ["o1", "o2"],
            "customer_id": ["c1", "c2"],
            "order_status": ["delivered", "canceled"],
            "order_purchase_timestamp": ["2024-01-01", "2024-01-03"],
            "order_approved_at": ["2024-01-01", "2024-01-03"],
            "order_delivered_carrier_date": ["2024-01-02", None],
            "order_delivered_customer_date": ["2024-01-05", None],
            "order_estimated_delivery_date": ["2024-01-04", "2024-01-10"],
        }
    ).to_csv(raw_dir / "olist_orders_dataset.csv", index=False)
    pd.DataFrame(
        {
            "order_id": ["o1", "o2"],
            "product_id": ["p1", "p2"],
            "seller_id": ["s1", "s1"],
            "price": [100.0, 50.0],
            "freight_value": [10.0, 5.0],
        }
    ).to_csv(raw_dir / "olist_order_items_dataset.csv", index=False)
    pd.DataFrame(
        {
            "review_id": ["r1", "r2"],
            "order_id": ["o1", "o2"],
            "review_score": [5, 2],
            "review_creation_date": ["2024-01-06", "2024-01-11"],
            "review_answer_timestamp": ["2024-01-07", "2024-01-12"],
        }
    ).to_csv(raw_dir / "olist_order_reviews_dataset.csv", index=False)
    pd.DataFrame(
        {
            "seller_id": ["s1"],
            "seller_zip_code_prefix": [12345],
            "seller_city": ["sao paulo"],
            "seller_state": ["sp"],
        }
    ).to_csv(raw_dir / "olist_sellers_dataset.csv", index=False)
    pd.DataFrame(
        {
            "product_id": ["p1", "p2"],
            "product_category_name": ["books", "electronics"],
        }
    ).to_csv(raw_dir / "olist_products_dataset.csv", index=False)


class DataExportTests(unittest.TestCase):
    def test_export_seller_report_creates_csv(self):
        metrics = _make_seller()
        path = export_seller_report(metrics, output_dir=Path("tmp_test_export"))
        self.assertTrue(path.exists())
        df = pd.read_csv(path)
        self.assertGreater(len(df), 0)
        self.assertIn("trust_score", df.columns)
        self.assertIn("risk_tier", df.columns)
        self.assertIn("recommended_action", df.columns)
        path.unlink()
        path.parent.rmdir()

    def test_export_filtered_report_by_tier(self):
        metrics = pd.concat([
            _make_seller(seller_id="s_good", late_delivery_rate=0.0, average_review_score=4.8),
            _make_seller(seller_id="s_bad", late_delivery_rate=0.9, average_review_score=1.2, negative_review_rate=0.9),
        ]).reset_index(drop=True)
        path = export_filtered_report(
            metrics, output_dir=Path("tmp_test_export"), risk_tier="low-risk"
        )
        self.assertTrue(path.exists())
        df = pd.read_csv(path)
        for tier in df["risk_tier"]:
            self.assertEqual(tier, "low-risk")
        path.unlink()
        path.parent.rmdir()

    def test_export_filtered_report_by_score_range(self):
        metrics = _make_seller()
        path = export_filtered_report(
            metrics, output_dir=Path("tmp_test_export"),
            min_trust_score=0, max_trust_score=100
        )
        self.assertTrue(path.exists())
        df = pd.read_csv(path)
        self.assertGreater(len(df), 0)
        path.unlink()
        path.parent.rmdir()

    def test_export_filtered_report_empty_when_no_match(self):
        metrics = _make_seller(late_delivery_rate=0.0, average_review_score=4.8)
        path = export_filtered_report(
            metrics, output_dir=Path("tmp_test_export"), risk_tier="high-risk"
        )
        self.assertTrue(path.exists())
        df = pd.read_csv(path)
        self.assertEqual(len(df), 0)
        path.unlink()
        path.parent.rmdir()

    def test_full_refresh_generates_outputs(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_dir = tmp_path / "raw"
            output_dir = tmp_path / "processed"
            _write_sample_raw_files(raw_dir)

            counts = full_refresh(
                raw_dir=raw_dir,
                output_dir=output_dir,
                db_path=output_dir / "test.db",
            )

            self.assertIn("seller_order_fact", counts)
            self.assertIn("seller_metrics", counts)
            self.assertIn("seller_report", counts)
            self.assertGreater(counts["seller_order_fact"], 0)
            self.assertGreater(counts["seller_metrics"], 0)
            self.assertGreater(counts["seller_report"], 0)

    def test_full_refresh_row_counts_are_integers(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_dir = tmp_path / "raw"
            output_dir = tmp_path / "processed"
            _write_sample_raw_files(raw_dir)

            counts = full_refresh(
                raw_dir=raw_dir,
                output_dir=output_dir,
                db_path=output_dir / "test.db",
            )

            for name, count in counts.items():
                self.assertIsInstance(count, int, f"{name} count should be an integer")


if __name__ == "__main__":
    unittest.main()
