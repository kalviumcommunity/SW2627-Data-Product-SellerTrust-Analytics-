"""Cross-validate dashboard metrics against the raw Olist CSVs (issue #28).

Picks a stratified random sample of sellers — by default two from each risk tier
plus the extremes of the trust distribution — and recomputes every headline
metric straight from the raw CSVs, deliberately without touching src/. If the
pipeline and this independent reimplementation disagree, one of them is wrong.

The sample is seeded, so a run is reproducible and a reported discrepancy can be
investigated by anyone.

A note on the reference implementation, because it is easy to get wrong: delivery
delay must be computed in *fractional* days. Using `Series.dt.days` floors a
negative timedelta towards minus infinity, so an order delivered 8.2 days early
is recorded as 9 days early and an order 3 hours late is recorded as on time.
That truncation makes the reference disagree with a correct pipeline by roughly
half a day per seller, in a consistent direction, which reads convincingly like a
pipeline bug and is not one.

Usage:
    python scripts/spot_check_sellers.py [--sample-size 10] [--seed 28]

Exits non-zero if any metric mismatches beyond tolerance.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

RATE_TOLERANCE = 0.001
DAYS_TOLERANCE = 0.01
SCORE_TOLERANCE = 0.01


def select_sellers(metrics: pd.DataFrame, sample_size: int, seed: int) -> pd.DataFrame:
    """Sample across risk tiers so the check is not dominated by one population."""
    tiers = sorted(metrics["risk_tier"].dropna().unique())
    per_tier = max(1, sample_size // (len(tiers) + 2))

    picks = [
        metrics[metrics["risk_tier"] == tier].sample(
            n=min(per_tier, int((metrics["risk_tier"] == tier).sum())),
            random_state=seed,
        )
        for tier in tiers
    ]

    # Anchor the sample on the extremes as well: the riskiest sellers and the
    # highest-volume ones are where a metric bug does the most damage.
    eligible = metrics[metrics["eligible_for_risk_score"]]
    picks.append(eligible.nsmallest(per_tier, "trust_score"))
    picks.append(eligible.nlargest(per_tier, "total_orders"))

    selected = pd.concat(picks).drop_duplicates(subset="seller_id")
    if len(selected) < sample_size:
        remaining = metrics[~metrics["seller_id"].isin(selected["seller_id"])]
        selected = pd.concat([selected, remaining.sample(n=sample_size - len(selected), random_state=seed)])
    return selected.head(sample_size).reset_index(drop=True)


def recompute_from_raw(seller_id: str, orders: pd.DataFrame, items: pd.DataFrame, reviews: pd.DataFrame) -> dict:
    """Recompute a seller's metrics from the raw CSVs, independently of src/."""
    order_ids = items.loc[items["seller_id"] == seller_id, "order_id"].unique()
    seller_orders = orders[orders["order_id"].isin(order_ids)]

    delivered = seller_orders[
        (seller_orders["order_status"] == "delivered")
        & seller_orders["order_delivered_customer_date"].notna()
        & seller_orders["order_estimated_delivery_date"].notna()
    ]

    if len(delivered) > 0:
        delivered_at = pd.to_datetime(delivered["order_delivered_customer_date"], format="ISO8601")
        estimated_at = pd.to_datetime(delivered["order_estimated_delivery_date"], format="ISO8601")
        # Fractional days on purpose — see the module docstring.
        delay_days = (delivered_at - estimated_at).dt.total_seconds() / 86400
        late_delivery_rate = float((delay_days > 0).mean())
        average_delivery_delay_days = float(delay_days.mean())
    else:
        late_delivery_rate = 0.0
        average_delivery_delay_days = float("nan")

    seller_reviews = reviews[reviews["order_id"].isin(order_ids)].dropna(subset=["review_score"])
    # One order, one voice. 547 of 98,673 orders carry more than one review row, and the
    # pipeline collapses those to a per-order mean before aggregating to the seller so a
    # single disputed order cannot outvote the rest. Averaging raw review rows instead
    # shifts a seller's score by up to ~0.015, which is why both are reported below.
    per_order = seller_reviews.groupby("order_id")["review_score"].mean()

    return {
        "total_orders": len(order_ids),
        "cancelled_orders": int((seller_orders["order_status"] == "canceled").sum()),
        "late_delivery_rate": late_delivery_rate,
        "average_delivery_delay_days": average_delivery_delay_days,
        "average_review_score": float(per_order.mean()) if len(per_order) else float("nan"),
        "negative_review_rate": float(per_order.le(2).mean()) if len(per_order) else float("nan"),
        "delivered_orders": len(delivered),
        "review_rows": len(seller_reviews),
        "reviewed_orders": len(per_order),
        "average_review_score_by_row": (
            float(seller_reviews["review_score"].mean()) if len(seller_reviews) else float("nan")
        ),
    }


def _compare(dashboard: float, raw: float, tolerance: float) -> tuple[bool, str]:
    both_missing = pd.isna(dashboard) and pd.isna(raw)
    if both_missing:
        return True, "both n/a"
    if pd.isna(dashboard) or pd.isna(raw):
        return False, f"dashboard={dashboard} raw={raw}"
    matched = abs(float(dashboard) - float(raw)) <= tolerance
    return matched, f"dashboard={float(dashboard):.4f} raw={float(raw):.4f}"


def run(raw_dir: Path, processed_dir: Path, sample_size: int, seed: int) -> int:
    metrics = pd.read_csv(processed_dir / "seller_metrics.csv")
    orders = pd.read_csv(raw_dir / "olist_orders_dataset.csv")
    items = pd.read_csv(raw_dir / "olist_order_items_dataset.csv")
    reviews = pd.read_csv(raw_dir / "olist_order_reviews_dataset.csv")

    selected = select_sellers(metrics, sample_size, seed)
    checks = [
        ("total_orders", 0),
        ("cancelled_orders", 0),
        ("late_delivery_rate", RATE_TOLERANCE),
        ("average_delivery_delay_days", DAYS_TOLERANCE),
        ("average_review_score", SCORE_TOLERANCE),
        ("negative_review_rate", RATE_TOLERANCE),
    ]

    print(f"Spot-checking {len(selected)} sellers against the raw CSVs (seed {seed})\n")
    mismatches: list[str] = []

    for position, row in selected.iterrows():
        seller_id = row["seller_id"]
        raw_metrics = recompute_from_raw(seller_id, orders, items, reviews)
        print(
            f"[{position + 1}] {seller_id}  tier={row['risk_tier']}  "
            f"orders={int(row['total_orders'])}  delivered={raw_metrics['delivered_orders']}  "
            f"reviews={raw_metrics['review_rows']} on {raw_metrics['reviewed_orders']} orders"
        )
        if raw_metrics["review_rows"] != raw_metrics["reviewed_orders"]:
            print(
                f"      note     an order carries more than one review; averaging review rows "
                f"instead of orders would give {raw_metrics['average_review_score_by_row']:.4f}"
            )
        for column, tolerance in checks:
            matched, detail = _compare(row[column], raw_metrics[column], tolerance)
            print(f"      {'MATCH   ' if matched else 'MISMATCH'} {column:28s} {detail}")
            if not matched:
                mismatches.append(f"{seller_id}:{column} ({detail})")
        print()

    total = len(selected) * len(checks)
    print(f"{total - len(mismatches)}/{total} metric comparisons match across {len(selected)} sellers")
    if mismatches:
        print(f"\n{len(mismatches)} MISMATCH(ES):")
        for mismatch in mismatches:
            print(f"  - {mismatch}")
        return 1
    print("No discrepancies found.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", default="data/raw", help="Directory containing the five Olist CSVs.")
    parser.add_argument("--processed-dir", default="data/processed", help="Directory holding the pipeline outputs.")
    parser.add_argument("--sample-size", type=int, default=10, help="How many sellers to check.")
    parser.add_argument("--seed", type=int, default=28, help="Random seed, so a run is reproducible.")
    args = parser.parse_args()
    return run(Path(args.raw_dir), Path(args.processed_dir), args.sample_size, args.seed)


if __name__ == "__main__":
    sys.exit(main())
