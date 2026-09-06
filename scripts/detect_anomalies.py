"""Command-line entry point for seller anomaly detection."""

import argparse
from pathlib import Path

from src.anomaly_detection import run_anomaly_detection


def main():
    parser = argparse.ArgumentParser(description="Detect anomalies in seller behaviour metrics.")
    parser.add_argument(
        "--input",
        default="data/processed/seller_metrics.csv",
        help="Path to seller_metrics.csv",
    )
    parser.add_argument(
        "--output",
        default="data/processed/seller_anomalies.csv",
        help="Path to output seller_anomalies.csv",
    )
    parser.add_argument(
        "--iqr-multiplier",
        type=float,
        default=1.5,
        help="IQR multiplier for outlier detection (default: 1.5)",
    )
    parser.add_argument(
        "--zscore-threshold",
        type=float,
        default=3.5,
        help="Z-score threshold for anomaly detection (default: 3.5)",
    )
    parser.add_argument(
        "--min-orders",
        type=int,
        default=5,
        help="Minimum order count before Z-score detection is applied (default: 5)",
    )
    parser.add_argument(
        "--no-exclude-early-deliveries",
        action="store_true",
        default=False,
        help="Include early deliveries (negative delay) in anomaly flags (off by default)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    anomalies = run_anomaly_detection(
        input_path=str(input_path),
        output_path=str(output_path),
        iqr_multiplier=args.iqr_multiplier,
        zscore_threshold=args.zscore_threshold,
        min_orders=args.min_orders,
        exclude_early_deliveries=not args.no_exclude_early_deliveries,
    )

    print(f"Wrote seller_anomalies.csv: {len(anomalies):,} sellers")
    print(f"  Any anomaly: {anomalies['any_anomaly'].sum():,}")
    print(f"  Mean anomaly count: {anomalies['anomaly_count'].mean():.2f}")


if __name__ == "__main__":
    main()
