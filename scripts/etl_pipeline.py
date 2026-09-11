"""End-to-end ETL pipeline: raw CSVs to all analytics outputs.

Usage:
    python scripts/etl_pipeline.py
    python scripts/etl_pipeline.py --skip-sql --skip-anomaly
    python scripts/etl_pipeline.py --raw-dir data/raw --output-dir data/processed
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Allow this file to be run directly from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logging_config import configure_pipeline_logging, get_pipeline_logger  # noqa: E402

log = get_pipeline_logger("etl")


def _run_etl_once(
    raw_dir: str = "data/raw",
    output_dir: str = "data/processed",
    db_path: str = "data/trust_analytics.db",
    log_dir: str = "logs",
    log_level: str | None = None,
    skip_sql: bool = False,
    skip_anomaly: bool = False,
    skip_actions: bool = False,
    skip_export: bool = False,
) -> dict[str, int]:
    """Run the full ETL pipeline with optional step skipping.

    Returns a dict of row counts per output. Raises on failure.
    """
    configure_pipeline_logging(log_dir=log_dir, level=log_level)
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
    from src.trust_score import calculate_trust_score

    metrics_path = Path(output_dir) / "seller_metrics.csv"
    from src.pipeline_cache import load_cached_csv

    metrics = load_cached_csv(metrics_path)
    scored = calculate_trust_score(metrics)
    scored.to_csv(metrics_path, index=False)
    scored.to_parquet(metrics_path.with_suffix(".parquet"), index=False)
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


def _write_run_metadata(output_dir: Path, run_id: str) -> None:
    metadata = {"run_id": run_id, "completed_at": datetime.now(UTC).isoformat()}
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (output_dir / ".gitkeep").touch()


def _publish_refresh(
    staged_output: Path,
    output_dir: Path,
    staged_db: Path,
    db_path: Path,
    run_id: str,
) -> None:
    output_backup = output_dir.parent / f".{output_dir.name}.backup-{run_id}"
    db_backup = db_path.parent / f".{db_path.name}.backup-{run_id}"
    output_published = False
    db_published = False
    try:
        if output_dir.exists():
            output_dir.rename(output_backup)
        staged_output.rename(output_dir)
        output_published = True
        if staged_db.exists():
            if db_path.exists():
                db_path.rename(db_backup)
            staged_db.rename(db_path)
            db_published = True
    except Exception:
        if db_published and db_path.exists():
            db_path.unlink()
        if db_backup.exists():
            db_backup.rename(db_path)
        if output_published and output_dir.exists():
            shutil.rmtree(output_dir)
        if output_backup.exists():
            output_backup.rename(output_dir)
        raise
    else:
        if output_backup.exists():
            shutil.rmtree(output_backup)
        if db_backup.exists():
            db_backup.unlink()


def _validate_staged_outputs(
    output_dir: Path,
    db_path: Path,
    *,
    skip_sql: bool,
    skip_anomaly: bool,
    skip_actions: bool,
    skip_export: bool,
) -> None:
    required = [
        "seller_order_fact.csv",
        "seller_order_fact.parquet",
        "seller_metrics.csv",
        "seller_metrics.parquet",
    ]
    if not skip_anomaly:
        required.append("seller_anomalies.csv")
    if not skip_actions:
        required.append("seller_report.csv")
    if not skip_export:
        required.extend(
            f"seller_report_{tier.lower().replace('-', '_')}.csv"
            for tier in ["High-Risk", "Return-Prone", "Inconsistent", "Reliable"]
        )
    missing = [name for name in required if not (output_dir / name).is_file()]
    if missing:
        raise RuntimeError(f"Staged refresh is incomplete; missing outputs: {', '.join(missing)}")
    if not skip_sql:
        if not db_path.is_file():
            raise RuntimeError("Staged refresh is incomplete; SQLite database was not created")
        conn = sqlite3.connect(str(db_path))
        try:
            for view in ("vw_seller_trust_metrics", "vw_category_risk", "vw_monthly_trends"):
                conn.execute(f"SELECT 1 FROM {view} LIMIT 1")
        finally:
            conn.close()


def run_etl(
    raw_dir: str = "data/raw",
    output_dir: str = "data/processed",
    db_path: str = "data/trust_analytics.db",
    log_dir: str = "logs",
    log_level: str | None = None,
    skip_sql: bool = False,
    skip_anomaly: bool = False,
    skip_actions: bool = False,
    skip_export: bool = False,
) -> dict[str, int]:
    """Run ETL in a private staging area and publish all outputs atomically."""
    output_path = Path(output_dir)
    database_path = Path(db_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output_path.parent / ".sellertrust-refresh.lock"
    run_id = uuid.uuid4().hex
    staged_output = output_path.parent / f".{output_path.name}.staging-{run_id}"
    db_stage_dir = output_path.parent if database_path.parent == output_path else database_path.parent
    staged_db = db_stage_dir / f".{database_path.name}.staging-{run_id}"

    try:
        lock_path.mkdir()
    except FileExistsError as exc:
        raise RuntimeError("Another data refresh is already in progress") from exc

    try:
        counts = _run_etl_once(
            raw_dir=raw_dir,
            output_dir=str(staged_output),
            db_path=str(staged_db),
            log_dir=log_dir,
            log_level=log_level,
            skip_sql=skip_sql,
            skip_anomaly=skip_anomaly,
            skip_actions=skip_actions,
            skip_export=skip_export,
        )
        _validate_staged_outputs(
            staged_output,
            staged_db,
            skip_sql=skip_sql,
            skip_anomaly=skip_anomaly,
            skip_actions=skip_actions,
            skip_export=skip_export,
        )
        _write_run_metadata(staged_output, run_id)
        _publish_refresh(staged_output, output_path, staged_db, database_path, run_id)
        return counts
    finally:
        try:
            if staged_output.exists():
                shutil.rmtree(staged_output)
            if staged_db.exists():
                staged_db.unlink()
        finally:
            if lock_path.exists():
                lock_path.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end ETL pipeline for Seller Trust Analytics.")
    parser.add_argument("--raw-dir", default="data/raw", help="Raw CSV directory.")
    parser.add_argument("--output-dir", default="data/processed", help="Output directory.")
    parser.add_argument("--db-path", default="data/trust_analytics.db", help="SQLite DB path.")
    parser.add_argument("--log-dir", default="logs", help="Directory for date-stamped pipeline logs.")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Log level. Defaults to PIPELINE_LOG_LEVEL or INFO.",
    )
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
            log_dir=args.log_dir,
            log_level=args.log_level,
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
