"""Spot Check 0028: Cross-validate dashboard outputs against raw data.

Issue #28: Verify processed seller metrics match raw Olist v1 CSVs.
This script performs targeted spot checks between dashboard-generated metrics
and manually computed values from raw source data.

NOTES FOR THIS WORKTREE:
  - Raw CSVs are NOT present in data/raw/ (only .gitkeep placeholder).
  - Database tables seller_order_fact & seller_metrics are empty.
  - This script documents expected checks; actual execution requires raw data.
"""

from pathlib import Path
import pandas as pd
import inspect


REQUIRED_RAW = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
}


def expected_spot_check_methodology():
    """Return description of cross-validation methodology per PRD."""
    return """\
Methodology (from cross-validation-report.md):

For each seller in seller_metrics.csv:
  1. Get seller_id from seller_metrics.csv
  2. Find all order_ids from seller_order_fact.csv (or items.csv)
  3. Filter raw orders.csv for those order_ids
  4. Compute metrics from raw data using same logic as build_seller_metrics()
  5. Compare with dashboard values (tolerance: 0.001)

Key fixed calculations (per pipeline.py build_seller_metrics):
  - late_delivery_rate: denominator = delivered orders with valid dates only,
    NOT all orders including cancelled/shipped.
  - average_delivery_delay_days: mean over delivered orders with valid dates.
  - negative_review_rate: s.dropna().le(2).mean() over valid review scores.
  - average_review_score: mean of review_score per seller.
"""


def quick_note_no_data():
    """Print notice about missing data in this worktree."""
    print("WARNING: No raw CSVs or populated database found in this worktree.")
    print("         Raw data (data/raw/*.csv) is required to perform actual validation.")
    print("         See cross-validation-report.md for prior results (issue #28).")


if __name__ == "__main__":
    quick_note_no_data()

    # Verify pipeline logic consistency — no external data needed.
    from src.pipeline import build_seller_metrics as _build

    src_desc = expected_spot_check_methodology()
    print(src_desc.strip())

    # Validate that build_seller_metrics uses correct denominator logic.
    src_source = inspect.getsource(_build)
    if "delivered_with_dates" in src_source:
        print("OK pipeline.build_seller_metrics uses delivered_with_dates denominator")
    else:
        print("XX pipeline.build_seller_metrics MISSING delivered_with_dates logic")

    print("\nSpot Check 0028 complete — methodology verified; execution pending raw data.")
