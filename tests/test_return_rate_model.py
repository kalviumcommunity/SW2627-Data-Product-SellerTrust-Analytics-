"""Tests for the next-month return rate model (issue #43)."""

import unittest

import numpy as np
import pandas as pd

from src.return_rate_model import (
    FEATURE_COLUMNS,
    build_seller_month_panel,
    predict_next_month,
    train_next_month_model,
)


def make_fact(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal seller-order fact frame from partial row specs."""
    defaults = {
        "order_id": None,
        "seller_id": "s1",
        "order_status": "delivered",
        "order_purchase_timestamp": "2018-01-15",
        "is_late_delivery": False,
        "delivery_delay_days": -1.0,
        "review_score": 5,
    }
    filled = []
    for index, row in enumerate(rows):
        merged = {**defaults, **row}
        merged["order_id"] = merged["order_id"] or f"o{index}"
        filled.append(merged)
    return pd.DataFrame(filled)


def month_of_orders(seller: str, month: str, count: int, cancelled: int = 0, negative: int = 0) -> list[dict]:
    """Generate `count` orders for one seller in one month, some cancelled or badly reviewed."""
    return [
        {
            "seller_id": seller,
            "order_id": f"{seller}-{month}-{i}",
            "order_purchase_timestamp": f"{month}-10",
            "order_status": "canceled" if i < cancelled else "delivered",
            "review_score": 1 if i < negative else 5,
        }
        for i in range(count)
    ]


class BuildPanelTests(unittest.TestCase):
    def test_panel_has_one_row_per_seller_month(self):
        fact = make_fact(month_of_orders("s1", "2018-01", 6) + month_of_orders("s1", "2018-02", 7))
        panel = build_seller_month_panel(fact)
        self.assertEqual(len(panel), 2)
        self.assertEqual(list(panel["total_orders"]), [6, 7])

    def test_months_below_the_order_floor_are_dropped(self):
        """A month with 2 orders cannot support a stable rate, so it must not enter the panel."""
        fact = make_fact(month_of_orders("s1", "2018-01", 6) + month_of_orders("s1", "2018-02", 2))
        panel = build_seller_month_panel(fact)
        self.assertEqual(len(panel), 1)
        self.assertEqual(str(panel.iloc[0]["month"]), "2018-01")

    def test_target_is_the_following_months_rate(self):
        fact = make_fact(
            month_of_orders("s1", "2018-01", 10, cancelled=0) + month_of_orders("s1", "2018-02", 10, cancelled=3)
        )
        panel = build_seller_month_panel(fact)
        january = panel[panel["month"].astype(str) == "2018-01"].iloc[0]
        self.assertAlmostEqual(january["cancellation_rate"], 0.0)
        self.assertAlmostEqual(january["next_month_cancellation_rate"], 0.3)

    def test_non_consecutive_months_do_not_become_the_target(self):
        """A gap in trading must not make a distant month masquerade as 'next month'."""
        fact = make_fact(
            month_of_orders("s1", "2018-01", 10, cancelled=0) + month_of_orders("s1", "2018-08", 10, cancelled=5)
        )
        panel = build_seller_month_panel(fact)
        january = panel[panel["month"].astype(str) == "2018-01"].iloc[0]
        self.assertTrue(pd.isna(january["next_month_cancellation_rate"]))

    def test_target_does_not_leak_across_sellers(self):
        fact = make_fact(
            month_of_orders("s1", "2018-01", 10, cancelled=0) + month_of_orders("s2", "2018-02", 10, cancelled=8)
        )
        panel = build_seller_month_panel(fact)
        first = panel[panel["seller_id"] == "s1"].iloc[0]
        self.assertTrue(pd.isna(first["next_month_cancellation_rate"]))

    def test_month_with_no_reviews_has_unknown_negative_rate(self):
        rows = month_of_orders("s1", "2018-01", 6)
        for row in rows:
            row["review_score"] = np.nan
        panel = build_seller_month_panel(make_fact(rows))
        self.assertTrue(pd.isna(panel.iloc[0]["negative_review_rate"]))


class TrainModelTests(unittest.TestCase):
    @staticmethod
    def _panel_over_months(n_sellers: int = 12, n_months: int = 12) -> pd.DataFrame:
        rows = []
        for seller in range(n_sellers):
            for month in range(1, n_months + 1):
                # A seller-specific cancellation level with a little month-to-month movement,
                # so the target is learnable rather than pure noise.
                cancelled = (seller + month) % 4
                rows += month_of_orders(f"s{seller}", f"2018-{month:02d}", 10, cancelled=cancelled, negative=seller % 5)
        return build_seller_month_panel(make_fact(rows))

    def test_split_is_by_time_not_at_random(self):
        result = train_next_month_model(self._panel_over_months())
        self.assertLess(result.train_months[1], result.test_months[0])

    def test_reports_r2_mae_and_both_baselines(self):
        result = train_next_month_model(self._panel_over_months())
        for value in (result.r2, result.mae, result.baseline_persistence_mae, result.baseline_mean_mae):
            self.assertFalse(np.isnan(value))
        self.assertGreaterEqual(result.mae, 0.0)
        self.assertEqual(set(result.coefficients), set(FEATURE_COLUMNS))

    def test_predictions_use_the_training_scaler(self):
        """Predicting must reapply the train-set standardisation, or the output is nonsense."""
        panel = self._panel_over_months()
        result = train_next_month_model(panel)
        rows = panel.dropna(subset=FEATURE_COLUMNS).head(5)
        predictions = predict_next_month(result, rows)
        self.assertEqual(len(predictions), 5)
        # Rates live in [0, 1]; a scaler mismatch throws predictions far outside that.
        self.assertTrue(np.all(np.abs(predictions) < 2.0))

    def test_missing_feature_column_is_rejected(self):
        panel = self._panel_over_months()
        result = train_next_month_model(panel)
        with self.assertRaises(ValueError):
            predict_next_month(result, panel.drop(columns=["late_delivery_rate"]))

    def test_unknown_target_is_rejected(self):
        with self.assertRaises(ValueError):
            train_next_month_model(self._panel_over_months(), target_column="next_month_nonsense")

    def test_too_little_history_is_rejected(self):
        fact = make_fact(month_of_orders("s1", "2018-01", 10) + month_of_orders("s1", "2018-02", 10))
        with self.assertRaises(ValueError):
            train_next_month_model(build_seller_month_panel(fact))


if __name__ == "__main__":
    unittest.main()
