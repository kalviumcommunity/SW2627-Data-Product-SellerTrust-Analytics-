"""End-to-end ETL pipeline: raw CSVs to all analytics outputs.

Usage:
    python scripts/etl_pipeline.py
    python scripts/etl_pipeline.py --skip-sql --skip-anomaly
    python scripts/etl_pipeline.py --raw-dir data/raw --output-dir data/processed
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("etl_pipeline")


def run_etl(
    raw_dir: str = "data/raw",
    output_dir: str = "data/processed",
    db_path: str = "data/trust_analytics.db",
    skip_sql: bool = False,
    skip_anomaly: bool = False,
    skip_actions: bool = False,
    skip_export: bool = False,
) -> dict[str, int]:
    """Run the full ETL pipeline with optional step skipping.

    Returns a dict of row counts per output. Raises on failure.
    """
    start = time.time()
    counts: dict[str, int] = {}

    # Step 1: Ingest and clean
    log.info("Step 1/6 — Ingesting and cleaning raw CSVs from %s", raw_dir)
    from src.pipeline import run_pipeline

    outputs = run_pipeline(raw_dir, output_dir)
    counts.update({name: len(frame) for name, frame in outputs.items()})
    log.info("  seller_order_fact: %s rows", counts.get("seller_order_fact", 0))
    log.info("  seller_metrics:    %s rows", counts.get("seller_metrics", 0))

    # Step 2: Trust scoring
    log.info("Step 2/6 — Computing trust scores")
    import pandas as pd

    from src.trust_score import calculate_trust_score

    metrics_path = Path(output_dir) / "seller_metrics.csv"
    metrics = pd.read_csv(metrics_path)
    scored = calculate_trust_score(metrics)
    scored.to_csv(metrics_path, index=False)
    log.info("  Trust scores computed for %s sellers", len(scored))

    # Step 3: Anomaly detection
    if not skip_anomaly:
        log.info("Step 3/6 — Running anomaly detection")
        from src.anomaly_detection import compute_seller_anomalies

        anomalies = compute_seller_anomalies(scored)
        anomaly_path = Path(output_dir) / "seller_anomalies.csv"
        anomalies.to_csv(anomaly_path, index=False)
        flagged = anomalies["any_anomaly"].sum()
        log.info("  %s sellers flagged with anomalies", flagged)
        counts["seller_anomalies"] = len(anomalies)
    else:
        log.info("Step 3/6 — Skipping anomaly detection")

    # Step 4: Action recommendations
    if not skip_actions:
        log.info("Step 4/6 — Generating action recommendations")
        from src.actions import recommend_actions

        report = recommend_actions(scored)
        report_path = Path(output_dir) / "seller_report.csv"
        report.to_csv(report_path, index=False)
        counts["seller_report"] = len(report)
        for action in ["Escalate", "Coach", "Monitor", "No Action"]:
            n = (report["recommended_action"] == action).sum()
            log.info("  %s: %s sellers", action, n)
    else:
        log.info("Step 4/6 — Skipping action recommendations")

    # Step 5: SQL load
    if not skip_sql:
        log.info("Step 5/6 — Loading into SQLite: %s", db_path)
        from src.sql_loader import load_to_sql

        sql_counts = load_to_sql(output_dir, db_path)
        counts.update(sql_counts)
        log.info("  Loaded %s rows into seller_order_fact", sql_counts.get("seller_order_fact", 0))
        log.info("  Loaded %s rows into seller_metrics", sql_counts.get("seller_metrics", 0))
    else:
        log.info("Step 5/6 — Skipping SQL load")

    # Step 6: Data export
    if not skip_export:
        log.info("Step 6/6 — Exporting filtered reports")
        from src.data_export import export_filtered_report

        for tier in ["High-Risk", "Return-Prone", "Inconsistent", "Reliable"]:
            path = export_filtered_report(
                scored,
                output_dir=output_dir,
                risk_tier=tier,
                filename=f"seller_report_{tier.lower().replace('-', '_')}.csv",
            )
            log.info("  Exported %s", path.name)
    else:
        log.info("Step 6/6 — Skipping data export")

    elapsed = time.time() - start
    log.info("ETL pipeline completed in %.1fs", elapsed)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end ETL pipeline for Seller Trust Analytics.")
    parser.add_argument("--raw-dir", default="data/raw", help="Raw CSV directory.")
    parser.add_argument("--output-dir", default="data/processed", help="Output directory.")
    parser.add_argument("--db-path", default="data/trust_analytics.db", help="SQLite DB path.")
    parser.add_argument("--skip-sql", action="store_true", help="Skip SQL database load.")
    parser.add_argument("--skip-anomaly", action="store_true", help="Skip anomaly detection.")
    parser.add_argument("--skip-actions", action="store_true", help="Skip action recommendations.")
    parser.add_argument("--skip-export", action="store_true", help="Skip filtered CSV export.")
    args = parser.parse_args()

    try:
        counts = run_etl(
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            db_path=args.db_path,
            skip_sql=args.skip_sql,
            skip_anomaly=args.skip_anomaly,
            skip_actions=args.skip_actions,
            skip_export=args.skip_export,
        )
        log.info("Output summary:")
        for name, count in counts.items():
            log.info("  %s: %s rows", name, count)
        return 0
    except Exception as exc:
        log.error("Pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
