"""Command-line entry point for assigning action tiers to sellers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.action_thresholds import (
    assign_action_tiers_batch,
    get_tier_recommendations,
)


def main():
    parser = argparse.ArgumentParser(description="Assign action tiers to sellers based on metrics.")
    parser.add_argument(
        "--input",
        default="data/processed/seller_metrics.csv",
        help="Path to seller_metrics.csv",
    )
    parser.add_argument(
        "--output",
        default="data/processed/seller_action_tiers.csv",
        help="Output path for action tiers CSV",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(input_path)
    tiers = assign_action_tiers_batch(df)
    df["action_tier"] = tiers

    for tier in df["action_tier"].unique():
        recs = get_tier_recommendations(tier)
        print(f"\n{tier.upper()} ({recs['priority']}):")
        for action in recs["actions"]:
            print(f"  - {action}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nWrote {len(df)} rows to {output_path}")


if __name__ == "__main__":
    main()
