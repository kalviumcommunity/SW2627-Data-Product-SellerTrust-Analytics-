"""Command-line entry point for seller review score trend detection."""

import argparse
from pathlib import Path

from src.trend_detection import run_trend_detection


def main():
    parser = argparse.ArgumentParser(description="Detect trends in seller review scores over time.")
    parser.add_argument(
        "--input",
        default="data/processed/seller_order_fact.csv",
        help="Path to seller_order_fact.csv",
    )
    parser.add_argument(
        "--output",
        default="data/processed/seller_trends.csv",
        help="Path to output seller_trends.csv",
    )
    parser.add_argument(
        "--time-column",
        default="order_purchase_timestamp",
        help="Column name for time variable",
    )
    parser.add_argument(
        "--score-column",
        default="review_score",
        help="Column name for review score",
    )
    parser.add_argument(
        "--seller-column",
        default="seller_id",
        help="Column name for seller ID",
    )
    parser.add_argument(
        "--min-orders",
        type=int,
        default=5,
        help="Minimum number of orders with reviews required for trend analysis",
    )
    parser.add_argument(
        "--p-value-threshold",
        type=float,
        default=0.05,
        help="P-value threshold for statistical significance",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    trends = run_trend_detection(
        input_path=str(input_path),
        output_path=str(output_path),
        time_column=args.time_column,
        score_column=args.score_column,
        seller_column=args.seller_column,
        min_orders=args.min_orders,
        p_value_threshold=args.p_value_threshold,
    )

    print(f"Wrote seller_trends.csv: {len(trends):,} sellers")
    print(f"  Declining: {(trends['trend_flag'] == 'declining').sum():,}")
    print(f"  Improving: {(trends['trend_flag'] == 'improving').sum():,}")
    print(f"  Stable: {(trends['trend_flag'] == 'stable').sum():,}")
    print(f"  Insufficient data: {(trends['trend_flag'] == 'insufficient_data').sum():,}")


if __name__ == "__main__":
    main()
