"""End-to-end validation of the pipeline outputs (issue #36).

Runs the full pipeline from the raw CSVs, then checks the result against the
invariants the dashboard depends on: row counts at each stage, seller coverage,
null trust scores, and value ranges. Every figure in docs/validation-report.md
comes from this script, so the report can be regenerated rather than hand-edited.

Usage:
    python scripts/validate_pipeline.py [--raw-dir data/raw] [--output-dir data/processed]

Exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.pipeline import run_pipeline

MIN_ORDERS_FOR_SCORE = 5


class Report:
    """Collects check results so a failure does not hide the checks after it."""

    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, name: str, passed: bool, detail: str = "") -> None:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}{f' — {detail}' if detail else ''}")
        if not passed:
            self.failures.append(name)


def validate(raw_dir: str, output_dir: str) -> int:
    report = Report()

    print("== Stage 1: run pipeline from raw ==")
    outputs = run_pipeline(raw_dir, output_dir)
    fact = outputs["seller_order_fact"]
    metrics = outputs["seller_metrics"]

    raw_orders = pd.read_csv(Path(raw_dir) / "olist_orders_dataset.csv")
    raw_items = pd.read_csv(Path(raw_dir) / "olist_order_items_dataset.csv")
    raw_reviews = pd.read_csv(Path(raw_dir) / "olist_order_reviews_dataset.csv")
    raw_sellers = pd.read_csv(Path(raw_dir) / "olist_sellers_dataset.csv")

    print("\n== Stage 2: row counts ==")
    print(f"  raw orders                : {len(raw_orders):,}")
    print(f"  raw order items           : {len(raw_items):,}")
    print(f"  raw reviews               : {len(raw_reviews):,}")
    print(f"  raw sellers               : {len(raw_sellers):,}")
    print(f"  seller-order fact rows    : {len(fact):,}")
    print(f"  distinct orders in fact   : {fact['order_id'].nunique():,}")
    print(f"  seller metrics rows       : {len(metrics):,}")

    selling_sellers = raw_items["seller_id"].nunique()
    report.check(
        "every seller with at least one item is scored",
        len(metrics) == selling_sellers,
        f"{len(metrics):,} metric rows vs {selling_sellers:,} sellers in the items table",
    )
    report.check(
        "no duplicate seller rows",
        metrics["seller_id"].is_unique,
        f"{metrics['seller_id'].nunique():,} distinct ids",
    )
    orders_with_items = raw_orders["order_id"].isin(raw_items["order_id"]).sum()
    report.check(
        "fact covers every order that has line items",
        fact["order_id"].nunique() == orders_with_items,
        f"{fact['order_id'].nunique():,} of {orders_with_items:,}",
    )

    print("\n== Stage 3: eligibility and trust scores ==")
    eligible = metrics[metrics["eligible_for_risk_score"]]
    ineligible = metrics[~metrics["eligible_for_risk_score"]]
    print(f"  eligible (>= {MIN_ORDERS_FOR_SCORE} orders)  : {len(eligible):,} ({len(eligible) / len(metrics):.1%})")
    print(f"  ineligible                : {len(ineligible):,} ({len(ineligible) / len(metrics):.1%})")

    report.check(
        "eligibility flag matches the order threshold",
        bool((metrics["eligible_for_risk_score"] == (metrics["total_orders"] >= MIN_ORDERS_FOR_SCORE)).all()),
    )
    report.check(
        "no eligible seller is missing a trust score",
        int(eligible["trust_score"].isna().sum()) == 0,
        f"{int(eligible['trust_score'].isna().sum())} nulls",
    )
    report.check(
        "every ineligible seller has a null trust score",
        int(ineligible["trust_score"].notna().sum()) == 0,
        f"{int(ineligible['trust_score'].notna().sum())} unexpected scores",
    )

    scores = eligible["trust_score"].astype(float)
    print(
        f"  trust score               : mean {scores.mean():.2f}  median {scores.median():.2f}  "
        f"std {scores.std():.2f}  range {scores.min():.2f}–{scores.max():.2f}"
    )
    report.check(
        "trust scores lie within 0-100",
        bool(((scores >= 0) & (scores <= 100)).all()),
    )

    print("\n== Stage 4: value ranges ==")
    rate_columns = ["late_delivery_rate", "negative_review_rate", "cancellation_rate_proxy"]
    for column in rate_columns:
        series = metrics[column].dropna()
        report.check(
            f"{column} within 0-1",
            bool(((series >= 0) & (series <= 1)).all()),
            f"range {series.min():.4f}–{series.max():.4f}",
        )
    reviews = metrics["average_review_score"].dropna()
    report.check(
        "average_review_score within 1-5",
        bool(((reviews >= 1) & (reviews <= 5)).all()),
        f"range {reviews.min():.2f}–{reviews.max():.2f}",
    )
    report.check(
        "no negative order counts",
        bool((metrics["total_orders"] > 0).all()),
    )
    report.check(
        "cancelled orders never exceed total orders",
        bool((metrics["cancelled_orders"] <= metrics["total_orders"]).all()),
    )

    print("\n== Stage 5: nulls per column ==")
    for column in metrics.columns:
        nulls = int(metrics[column].isna().sum())
        print(f"  {column:32s} {nulls:>6,}")

    print("\n== Stage 6: risk tier coverage ==")
    report.check(
        "every seller has a risk tier",
        int(metrics["risk_tier"].isna().sum()) == 0,
    )
    for tier, count in metrics["risk_tier"].value_counts().items():
        print(f"  {tier:12s} {count:>6,} ({count / len(metrics):.1%})")

    print()
    if report.failures:
        print(f"VALIDATION FAILED — {len(report.failures)} check(s): {', '.join(report.failures)}")
        return 1
    print("VALIDATION PASSED — all checks green")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", default="data/raw", help="Directory containing the five Olist CSVs.")
    parser.add_argument("--output-dir", default="data/processed", help="Directory for generated CSV outputs.")
    args = parser.parse_args()
    return validate(args.raw_dir, args.output_dir)


if __name__ == "__main__":
    sys.exit(main())
