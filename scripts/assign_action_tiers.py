"""Command-line entry point for assigning action tiers to sellers."""

import sys
import os

# Debug: print path info
print(f"__file__ = {__file__}", file=sys.stderr)
print(f"cwd = {os.getcwd()}", file=sys.stderr)

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"project_root = {project_root}", file=sys.stderr)
sys.path.insert(0, project_root)

print(f"sys.path[0] = {sys.path[0]}", file=sys.stderr)

import argparse
from pathlib import Path
import pandas as pd

print("About to import action_thresholds", file=sys.stderr)
from src.action_thresholds import (
    ActionThresholds,
    assign_action_tiers_batch,
    get_tier_recommendations,
)
print("Imported successfully", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Assign action tiers to sellers based on metrics."
    )
    parser.add_argument(
        "--input",
        default="data/processed/seller_metrics.csv",
        help="Path to seller_metrics.csv",
    )
    parser.add_argument(
        "--anomalies",
        default="data/processed/seller_anomalies.csv",
        help="Path to seller_anomalies.csv",
    )
    parser.add_argument(
        "--trends",
        default="data/processed/seller_trends.csv",
        help="Path to seller_trends.csv",
    )
    parser.add_argument(
        "--output",
        default="data/processed/seller_action_tiers.csv",
        help="Path to output seller_action_tiers.csv",
    )
    parser.add_argument(
        "--config",
        help="Path to JSON config file with custom thresholds",
    )
    args = parser.parse_args()

    # Load thresholds
    if args.config:
        thresholds = ActionThresholds.load_from_file(args.config)
    else:
        thresholds = ActionThresholds()

    # Load data
    metrics = pd.read_csv(args.input)
    anomalies = pd.read_csv(args.anomalies)
    trends = pd.read_csv(args.trends)

    # Merge anomaly count and trend flag
    metrics = metrics.merge(
        anomalies[["seller_id", "anomaly_count"]],
        on="seller_id",
        how="left"
    )
    metrics["anomaly_count"] = metrics["anomaly_count"].fillna(0).astype(int)

    metrics = metrics.merge(
        trends[["seller_id", "trend_flag"]],
        on="seller_id",
        how="left"
    )
    metrics["declining_trend"] = metrics["trend_flag"] == "declining"

    # Calculate return rate (using cancellation_rate_proxy as proxy)
    metrics["return_rate"] = metrics["cancellation_rate_proxy"]

    # Calculate seller age (days since first order)
    fact = pd.read_csv("data/processed/seller_order_fact.csv")
    fact["order_purchase_timestamp"] = pd.to_datetime(fact["order_purchase_timestamp"])
    first_order = fact.groupby("seller_id")["order_purchase_timestamp"].min().reset_index()
    first_order.columns = ["seller_id", "first_order_date"]
    last_order = fact.groupby("seller_id")["order_purchase_timestamp"].max().reset_index()
    last_order.columns = ["seller_id", "last_order_date"]

    metrics = metrics.merge(first_order, on="seller_id", how="left")
    metrics = metrics.merge(last_order, on="seller_id", how="left")

    # Calculate seller age in days (using max date in dataset as reference)
    max_date = fact["order_purchase_timestamp"].max()
    metrics["seller_age_days"] = (max_date - metrics["first_order_date"]).dt.days

    # Assign action tiers
    metrics["action_tier"] = assign_action_tiers_batch(metrics, thresholds)

    # Add recommendations
    recommendations = metrics["action_tier"].apply(get_tier_recommendations)
    metrics["priority"] = recommendations.apply(lambda x: x["priority"])
    metrics["review_frequency"] = recommendations.apply(lambda x: x["review_frequency"])

    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(output_path, index=False)

    # Print summary
    tier_counts = metrics["action_tier"].value_counts()
    print(f"Wrote seller_action_tiers.csv: {len(metrics):,} sellers")
    for tier, count in tier_counts.items():
        pct = count / len(metrics) * 100
        print(f"  {tier.capitalize()}: {count:,} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
