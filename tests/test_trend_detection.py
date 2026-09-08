"""Tests for seller review-score trend detection (issue #18).

The module was shipped without unit tests. These pin the behaviour that the
`trend_flag` column depends on: the two-part significance rule, the minimum
order floor, and the fact that a seller with no reviews drops out of the output
entirely rather than appearing as `insufficient_data`.
"""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from src.trend_detection import compute_seller_review_trends, run_trend_detection


def seller_frame(seller_id: str, scores: list, start: datetime | None = None, spacing_days: int = 30) -> pd.DataFrame:
    """One seller's review history, one order per point, evenly spaced in time."""
    start = start or datetime(2018, 1, 1)
    return pd.DataFrame(
        {
            "seller_id": [seller_id] * len(scores),
            "order_id": [f"{seller_id}-o{i}" for i in range(len(scores))],
            "order_purchase_timestamp": [start + timedelta(days=i * spacing_days) for i in range(len(scores))],
            "review_score": scores,
        }
    )


class TrendFlagTests(unittest.TestCase):
    def test_clear_downward_slope_is_declining(self):
        result = compute_seller_review_trends(seller_frame("s1", [5, 5, 4, 4, 3, 3, 2, 2, 1, 1]))
        row = result.iloc[0]
        self.assertEqual(row["trend_flag"], "declining")
        self.assertLess(row["slope"], 0)
        self.assertLess(row["p_value"], 0.05)

    def test_clear_upward_slope_is_improving(self):
        result = compute_seller_review_trends(seller_frame("s1", [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]))
        row = result.iloc[0]
        self.assertEqual(row["trend_flag"], "improving")
        self.assertGreater(row["slope"], 0)
        self.assertLess(row["p_value"], 0.05)

    def test_noisy_history_is_stable_not_a_trend(self):
        """A slope exists in almost any sample; without significance it is not a trend."""
        result = compute_seller_review_trends(seller_frame("s1", [3, 5, 1, 4, 2, 5, 1, 3, 4, 2]))
        row = result.iloc[0]
        self.assertEqual(row["trend_flag"], "stable")
        self.assertGreaterEqual(row["p_value"], 0.05)

    def test_flat_history_is_stable(self):
        result = compute_seller_review_trends(seller_frame("s1", [4, 4, 4, 4, 4, 4]))
        self.assertEqual(result.iloc[0]["trend_flag"], "stable")

    def test_significance_alone_does_not_flag_a_direction(self):
        """Both halves of the rule matter: p < 0.05 *and* a signed slope."""
        declining = compute_seller_review_trends(seller_frame("s1", [5, 5, 4, 4, 3, 3, 2, 2, 1, 1])).iloc[0]
        # Raising the bar past the observed p-value must demote the same data to stable.
        stricter = compute_seller_review_trends(
            seller_frame("s1", [5, 5, 4, 4, 3, 3, 2, 2, 1, 1]),
            p_value_threshold=declining["p_value"] / 2,
        ).iloc[0]
        self.assertEqual(declining["trend_flag"], "declining")
        self.assertEqual(stricter["trend_flag"], "stable")


class EligibilityTests(unittest.TestCase):
    def test_below_the_order_floor_is_insufficient_data(self):
        result = compute_seller_review_trends(seller_frame("s1", [5, 4, 3, 2]))
        row = result.iloc[0]
        self.assertEqual(row["trend_flag"], "insufficient_data")
        self.assertEqual(row["n_reviews"], 4)
        self.assertTrue(pd.isna(row["slope"]))
        self.assertTrue(pd.isna(row["p_value"]))

    def test_order_floor_is_configurable(self):
        frame = seller_frame("s1", [5, 4, 3, 2])
        self.assertEqual(compute_seller_review_trends(frame, min_orders=4).iloc[0]["trend_flag"], "declining")
        self.assertEqual(compute_seller_review_trends(frame, min_orders=5).iloc[0]["trend_flag"], "insufficient_data")

    def test_seller_with_no_reviews_is_absent_from_the_output(self):
        """This is why the pipeline reports 3,090 sellers rather than 3,095.

        Rows without a review score are dropped before grouping, so a seller whose
        every order is unreviewed never forms a group and gets no row at all — not
        even an `insufficient_data` one.
        """
        reviewed = seller_frame("s1", [5, 4, 3, 5, 4])
        unreviewed = seller_frame("s2", [np.nan] * 3)
        result = compute_seller_review_trends(pd.concat([reviewed, unreviewed], ignore_index=True))
        self.assertEqual(list(result["seller_id"]), ["s1"])

    def test_unreviewed_orders_do_not_count_towards_the_floor(self):
        frame = pd.concat([seller_frame("s1", [5, 4, 3]), seller_frame("s1", [np.nan] * 4)], ignore_index=True)
        self.assertEqual(compute_seller_review_trends(frame).iloc[0]["trend_flag"], "insufficient_data")


class InputHandlingTests(unittest.TestCase):
    def test_sellers_are_scored_independently(self):
        frame = pd.concat(
            [
                seller_frame("falling", [5, 5, 4, 4, 3, 3, 2, 2, 1, 1]),
                seller_frame("rising", [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]),
            ],
            ignore_index=True,
        )
        flags = compute_seller_review_trends(frame).set_index("seller_id")["trend_flag"].to_dict()
        self.assertEqual(flags, {"falling": "declining", "rising": "improving"})

    def test_unparseable_scores_and_dates_are_coerced_not_raised(self):
        frame = seller_frame("s1", [5, 4, 3, 2, 1, 1])
        # Cast first: pandas 2.x deprecates assigning an incompatible dtype in place, and
        # the point of the test is the module's coercion, not the fixture's.
        frame["review_score"] = frame["review_score"].astype(object)
        frame["order_purchase_timestamp"] = frame["order_purchase_timestamp"].astype(str)
        frame.loc[0, "review_score"] = "not a number"
        frame.loc[1, "order_purchase_timestamp"] = "not a date"
        result = compute_seller_review_trends(frame)
        self.assertEqual(result.iloc[0]["n_reviews"], 4)

    def test_output_carries_every_column_the_report_reads(self):
        result = compute_seller_review_trends(seller_frame("s1", [5, 4, 3, 2, 1, 1]))
        for column in ("seller_id", "n_reviews", "slope", "intercept", "r_value", "p_value", "std_err", "trend_flag"):
            self.assertIn(column, result.columns)


class RunTrendDetectionTests(unittest.TestCase):
    def test_writes_a_csv_and_returns_the_same_frame(self):
        with TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "seller_order_fact.csv"
            destination = Path(temp_dir) / "seller_trends.csv"
            seller_frame("s1", [5, 5, 4, 4, 3, 3, 2, 2, 1, 1]).to_csv(source, index=False)

            returned = run_trend_detection(str(source), str(destination))

            self.assertTrue(destination.exists())
            written = pd.read_csv(destination)
            self.assertEqual(len(written), len(returned))
            self.assertEqual(written.iloc[0]["trend_flag"], "declining")


if __name__ == "__main__":
    unittest.main()
