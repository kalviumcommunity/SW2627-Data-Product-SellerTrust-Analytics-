"""Train and evaluate the next-month return rate model (issue #43).

Builds a seller-month panel from the processed fact table, fits a linear
regression on month t's signals to predict month t+1, and reports R2 and MAE
against two baselines. Run the pipeline first so data/processed exists.

Usage:
    python scripts/train_return_rate_model.py
    python scripts/train_return_rate_model.py --target next_month_negative_review_rate
    python scripts/train_return_rate_model.py --all-targets
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.return_rate_model import (
    FEATURE_COLUMNS,
    LAGGED_RATES,
    TARGET_COLUMN,
    build_seller_month_panel,
    train_next_month_model,
)

TRAILING_FEATURES = [
    "trailing3_cancellation_rate",
    "trailing3_negative_review_rate",
    "trailing3_late_delivery_rate",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--processed-dir", default="data/processed", help="Directory holding the pipeline outputs.")
    parser.add_argument("--target", default=TARGET_COLUMN, help="Which next_month_* column to predict.")
    parser.add_argument("--all-targets", action="store_true", help="Evaluate every lagged rate in turn.")
    parser.add_argument("--no-trailing", action="store_true", help="Use only current-month signals.")
    args = parser.parse_args()

    fact_path = Path(args.processed_dir) / "seller_order_fact.csv"
    if not fact_path.exists():
        print(f"Missing {fact_path}. Run scripts/run_pipeline.py first.", file=sys.stderr)
        return 1

    panel = build_seller_month_panel(pd.read_csv(fact_path))
    features = FEATURE_COLUMNS if args.no_trailing else FEATURE_COLUMNS + TRAILING_FEATURES

    print(f"Seller-month panel: {len(panel):,} rows, {panel['seller_id'].nunique():,} sellers, "
          f"{panel['month'].nunique()} months ({panel['month'].min()} to {panel['month'].max()})\n")

    targets = [f"next_month_{rate}" for rate in LAGGED_RATES] if args.all_targets else [args.target]
    for target in targets:
        result = train_next_month_model(panel, target_column=target, feature_columns=features)
        print(result.summary())
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
