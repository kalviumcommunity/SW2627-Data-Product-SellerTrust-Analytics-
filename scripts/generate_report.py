"""Generate a single-seller health report as standalone HTML (issue #46).

Reads the pipeline outputs in data/processed and writes one self-contained HTML
file per seller, covering trust score, every metric, the review-score trend,
detected anomalies and the recommended action with its supporting evidence.

Usage:
    python scripts/generate_report.py --seller-id SELLER_123
    python scripts/generate_report.py --seller-id SELLER_123 --output-dir reports
    python scripts/generate_report.py --list-riskiest 5

Exits non-zero if the seller id is unknown or the pipeline has not been run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.actions import recommend_actions
from src.seller_report import (
    SellerNotFoundError,
    build_history_chart,
    collect_seller_report,
    render_report,
)


def load_inputs(processed_dir: Path) -> dict[str, pd.DataFrame | None]:
    """Load the pipeline outputs. Trends and anomalies are optional; the rest is not."""
    metrics_path = processed_dir / "seller_metrics.csv"
    fact_path = processed_dir / "seller_order_fact.csv"
    for path in (metrics_path, fact_path):
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path}. Run: python scripts/run_pipeline.py --raw-dir data/raw --output-dir {processed_dir}"
            )

    optional = {}
    for key, filename in (("trends", "seller_trends.csv"), ("anomalies", "seller_anomalies.csv")):
        path = processed_dir / filename
        optional[key] = pd.read_csv(path) if path.exists() else None

    return {"metrics": pd.read_csv(metrics_path), "fact": pd.read_csv(fact_path), **optional}


def generate(seller_id: str, inputs: dict, output_dir: Path, with_chart: bool = True) -> Path:
    """Write one seller's report and return the path it was written to."""
    metrics = inputs["metrics"]

    # recommend_actions works over the whole frame; slice out this seller afterwards.
    try:
        actions = recommend_actions(metrics)
    except Exception as error:  # noqa: BLE001 - a report is still useful without the recommendation
        print(f"warning: could not compute recommendations ({error}); continuing without them", file=sys.stderr)
        actions = None

    report = collect_seller_report(
        seller_id,
        metrics=metrics,
        fact=inputs["fact"],
        trends=inputs["trends"],
        anomalies=inputs["anomalies"],
        actions=actions,
    )
    chart_html = build_history_chart(report["history"], seller_id) if with_chart else ""

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"seller_report_{seller_id}.html"
    destination.write_text(render_report(report, chart_html), encoding="utf-8")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seller-id", help="Seller to report on.")
    parser.add_argument("--processed-dir", default="data/processed", help="Directory holding the pipeline outputs.")
    parser.add_argument("--output-dir", default="reports", help="Where to write the HTML report.")
    parser.add_argument("--no-chart", action="store_true", help="Skip the embedded Plotly chart.")
    parser.add_argument(
        "--list-riskiest",
        type=int,
        metavar="N",
        help="Print the N lowest-trust seller ids and exit, so you have something to pass to --seller-id.",
    )
    args = parser.parse_args()

    try:
        inputs = load_inputs(Path(args.processed_dir))
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return 1

    if args.list_riskiest:
        metrics = inputs["metrics"]
        if metrics is None:
            raise RuntimeError("Metrics data is required to list riskiest sellers")
        eligible = metrics[metrics["eligible_for_risk_score"]]
        for _, row in eligible.nsmallest(args.list_riskiest, "trust_score").iterrows():
            print(f"{row['seller_id']}  trust {float(row['trust_score']):5.2f}  {row['risk_tier']}")
        return 0

    if not args.seller_id:
        parser.error("--seller-id is required (or use --list-riskiest to find one)")

    try:
        destination = generate(args.seller_id, inputs, Path(args.output_dir), with_chart=not args.no_chart)
    except SellerNotFoundError as error:
        print(error, file=sys.stderr)
        print("Try: python scripts/generate_report.py --list-riskiest 5", file=sys.stderr)
        return 1

    print(f"Wrote {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
