"""Compute every figure quoted in docs/analytics-summary.md (issue #39).

The summary document is a set of claims about the marketplace; this script is
where those claims come from. Re-run it after a pipeline change and the numbers
in the document can be refreshed against real output instead of being edited by
hand.

Reads the processed outputs, so run the pipeline first:
    python scripts/run_pipeline.py --raw-dir data/raw --output-dir data/processed
    python scripts/detect_trends.py
    python scripts/detect_anomalies.py
    python scripts/analytics_summary.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from scipy import stats

TOP_N = 10


def _load(processed_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load seller metrics joined to trends and anomalies, plus the order-level fact table."""
    metrics = pd.read_csv(processed_dir / "seller_metrics.csv")

    trends_path = processed_dir / "seller_trends.csv"
    if trends_path.exists():
        trends = pd.read_csv(trends_path)[["seller_id", "slope", "p_value", "trend_flag"]]
        metrics = metrics.merge(trends, on="seller_id", how="left")
        metrics["trend_flag"] = metrics["trend_flag"].fillna("insufficient_data")
    else:
        metrics["trend_flag"] = "insufficient_data"

    anomalies_path = processed_dir / "seller_anomalies.csv"
    if anomalies_path.exists():
        anomalies = pd.read_csv(anomalies_path)
        count_column = next(
            (c for c in ("anomaly_count", "total_anomalies", "n_anomalies") if c in anomalies.columns),
            None,
        )
        if count_column:
            metrics = metrics.merge(
                anomalies[["seller_id", count_column]].rename(columns={count_column: "anomaly_count"}),
                on="seller_id",
                how="left",
            )
    if "anomaly_count" not in metrics.columns:
        metrics["anomaly_count"] = 0
    metrics["anomaly_count"] = metrics["anomaly_count"].fillna(0).astype(int)

    fact = pd.read_csv(processed_dir / "seller_order_fact.csv")
    return metrics, fact


def _correlate(label: str, left: pd.Series, right: pd.Series) -> None:
    pair = pd.concat([left, right], axis=1).dropna()
    if len(pair) < 3:
        print(f"  {label:56s} insufficient data")
        return
    r, p = stats.pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])
    p_text = "< 0.001" if p < 0.001 else f"{p:.4f}"
    print(f"  {label:56s} r = {r:+.3f}   p {p_text}   n = {len(pair):,}")


def summarise(processed_dir: Path) -> int:
    metrics, fact = _load(processed_dir)
    eligible = metrics[metrics["eligible_for_risk_score"]].copy()

    print("== Population ==")
    print(f"  sellers                      : {len(metrics):,}")
    print(f"  eligible (>= 5 orders)       : {len(eligible):,} ({len(eligible) / len(metrics):.1%})")
    scores = eligible["trust_score"].astype(float)
    q1, q2, q3 = scores.quantile([0.25, 0.5, 0.75])
    print(f"  trust score mean / median    : {scores.mean():.2f} / {scores.median():.2f}")
    print(f"  trust score std / range      : {scores.std():.2f} / {scores.min():.2f}-{scores.max():.2f}")
    print(f"  trust score Q1 / Q2 / Q3     : {q1:.2f} / {q2:.2f} / {q3:.2f}")
    print("  risk tiers (all sellers)     :")
    for tier, count in metrics["risk_tier"].value_counts().items():
        print(f"      {tier:10s} {count:>6,} ({count / len(metrics):.1%})")
    print("  trend flags (all sellers)    :")
    for flag, count in metrics["trend_flag"].value_counts().items():
        print(f"      {flag:20s} {count:>6,} ({count / len(metrics):.1%})")
    flagged = int((eligible["anomaly_count"] > 0).sum())
    print(f"  eligible with >=1 anomaly    : {flagged:,} ({flagged / len(eligible):.1%})")
    print(f"  mean anomalies per eligible  : {eligible['anomaly_count'].mean():.2f}")

    print(f"\n== Top {TOP_N} riskiest sellers (lowest trust score among eligible) ==")
    columns = [
        "seller_id",
        "trust_score",
        "total_orders",
        "late_delivery_rate",
        "average_review_score",
        "negative_review_rate",
        "cancellation_rate_proxy",
        "anomaly_count",
        "trend_flag",
    ]
    riskiest = eligible.nsmallest(TOP_N, "trust_score")[columns]
    for rank, (_, row) in enumerate(riskiest.iterrows(), start=1):
        print(
            f"  {rank:>2}. {row['seller_id']}  trust {float(row['trust_score']):5.2f}  "
            f"orders {int(row['total_orders']):>3}  late {row['late_delivery_rate']:.1%}  "
            f"review {row['average_review_score']:.2f}  neg {row['negative_review_rate']:.1%}  "
            f"cancel {row['cancellation_rate_proxy']:.1%}  anomalies {int(row['anomaly_count'])}  "
            f"{row['trend_flag']}"
        )
    print("  --- ranges across the top 10 ---")
    print(f"  late delivery rate  : {riskiest['late_delivery_rate'].min():.1%} - {riskiest['late_delivery_rate'].max():.1%}")
    print(f"  average review      : {riskiest['average_review_score'].min():.2f} - {riskiest['average_review_score'].max():.2f}")
    print(f"  negative review rate: {riskiest['negative_review_rate'].min():.1%} - {riskiest['negative_review_rate'].max():.1%}")

    print("\n== Trust-erosion patterns (eligible sellers) ==")
    patterns = {
        "A late delivery > 30% AND negative reviews > 30%":
            (eligible["late_delivery_rate"] > 0.30) & (eligible["negative_review_rate"] > 0.30),
        "B average review < 3.5 AND late delivery > 20%":
            (eligible["average_review_score"] < 3.5) & (eligible["late_delivery_rate"] > 0.20),
        "C cancellation > 30% AND negative reviews > 30%":
            (eligible["cancellation_rate_proxy"] > 0.30) & (eligible["negative_review_rate"] > 0.30),
        "D declining trend AND >= 2 anomalies":
            (eligible["trend_flag"] == "declining") & (eligible["anomaly_count"] >= 2),
        "E negative reviews > 30% alone":
            eligible["negative_review_rate"] > 0.30,
        "F late delivery > 30% alone":
            eligible["late_delivery_rate"] > 0.30,
    }
    for label, mask in patterns.items():
        subset = eligible[mask]
        share = len(subset) / len(eligible)
        mean_trust = subset["trust_score"].astype(float).mean() if len(subset) else float("nan")
        print(f"  {label:52s} {len(subset):>4,} ({share:5.1%})  mean trust {mean_trust:6.2f}")

    print("\n== Correlations: delivery delay vs negative reviews ==")
    print("  Seller level (eligible sellers)")
    _correlate("late delivery rate  vs negative review rate", eligible["late_delivery_rate"], eligible["negative_review_rate"])
    _correlate("late delivery rate  vs average review score", eligible["late_delivery_rate"], eligible["average_review_score"])
    _correlate("avg delivery delay  vs negative review rate", eligible["average_delivery_delay_days"], eligible["negative_review_rate"])
    _correlate("late delivery rate  vs trust score", eligible["late_delivery_rate"], eligible["trust_score"].astype(float))
    _correlate("late delivery rate  vs cancellation rate", eligible["late_delivery_rate"], eligible["cancellation_rate_proxy"])

    print("  Order level (delivered orders with a review)")
    orders = fact.dropna(subset=["delivery_delay_days", "review_score"]).copy()
    orders["is_negative"] = orders["review_score"].le(2).astype(int)
    _correlate("delivery delay days vs review score", orders["delivery_delay_days"], orders["review_score"])
    _correlate("delivery delay days vs negative review (0/1)", orders["delivery_delay_days"], orders["is_negative"])

    print("\n  Negative review rate by delivery outcome (order level)")
    buckets = [
        ("early or on time (delay <= 0)", orders["delivery_delay_days"] <= 0),
        ("late 0-3 days", (orders["delivery_delay_days"] > 0) & (orders["delivery_delay_days"] <= 3)),
        ("late 3-7 days", (orders["delivery_delay_days"] > 3) & (orders["delivery_delay_days"] <= 7)),
        ("late 7-14 days", (orders["delivery_delay_days"] > 7) & (orders["delivery_delay_days"] <= 14)),
        ("late more than 14 days", orders["delivery_delay_days"] > 14),
    ]
    for label, mask in buckets:
        subset = orders[mask]
        if len(subset) == 0:
            continue
        print(
            f"    {label:32s} n = {len(subset):>6,}   negative {subset['is_negative'].mean():6.1%}   "
            f"mean review {subset['review_score'].mean():.2f}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--processed-dir", default="data/processed", help="Directory holding the pipeline outputs.")
    args = parser.parse_args()
    return summarise(Path(args.processed_dir))


if __name__ == "__main__":
    sys.exit(main())
