import unittest
from pathlib import Path

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
        counts = full_refresh(
            raw_dir="data/raw",
            output_dir=Path("tmp_test_full_refresh"),
            db_path=Path("tmp_test_full_refresh/test.db"),
        )
        self.assertIn("seller_order_fact", counts)
        self.assertIn("seller_metrics", counts)
        self.assertIn("seller_report", counts)
        self.assertGreater(counts["seller_order_fact"], 0)
        self.assertGreater(counts["seller_metrics"], 0)
        self.assertGreater(counts["seller_report"], 0)

        for fname in ["seller_order_fact.csv", "seller_metrics.csv", "seller_report.csv"]:
            (Path("tmp_test_full_refresh") / fname).unlink()
        Path("tmp_test_full_refresh/test.db").unlink()
        Path("tmp_test_full_refresh").rmdir()

    def test_full_refresh_row_counts_are_integers(self):
        counts = full_refresh(
            raw_dir="data/raw",
            output_dir=Path("tmp_test_full_refresh"),
            db_path=Path("tmp_test_full_refresh/test.db"),
        )
        for name, count in counts.items():
            self.assertIsInstance(count, int, f"{name} count should be an integer")

        for fname in ["seller_order_fact.csv", "seller_metrics.csv", "seller_report.csv"]:
            (Path("tmp_test_full_refresh") / fname).unlink()
        Path("tmp_test_full_refresh/test.db").unlink()
        Path("tmp_test_full_refresh").rmdir()


if __name__ == "__main__":
    unittest.main()
