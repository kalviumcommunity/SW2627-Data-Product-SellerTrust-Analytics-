"""Data export: generates filtered seller reports and manages pipeline outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.trust_score import calculate_trust_score
from src.anomaly_detection import detect_anomalies
from src.actions import recommend_actions
from src.sql_loader import load_to_sql, DEFAULT_DB_PATH


DEFAULT_OUTPUT_DIR = Path("data/processed")


def export_seller_report(
    seller_metrics: pd.DataFrame,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    filename: str = "seller_report.csv",
) -> Path:
    """Export a full seller report with trust scores, anomalies, and actions to CSV."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    report = recommend_actions(seller_metrics)
    report_path = output_path / filename
    report.to_csv(report_path, index=False)
    return report_path


def export_filtered_report(
    seller_metrics: pd.DataFrame,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    risk_tier: str | None = None,
    min_trust_score: float | None = None,
    max_trust_score: float | None = None,
    filename: str = "seller_filtered_report.csv",
) -> Path:
    """Export a filtered seller report based on risk tier or trust score range."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    report = recommend_actions(seller_metrics)

    if risk_tier is not None:
        report = report[report["risk_tier"] == risk_tier]
    if min_trust_score is not None:
        report = report[report["trust_score"] >= min_trust_score]
    if max_trust_score is not None:
        report = report[report["trust_score"] <= max_trust_score]

    report_path = output_path / filename
    report.to_csv(report_path, index=False)
    return report_path


def full_refresh(
    raw_dir: str | Path = "data/raw",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, int]:
    """Run the complete pipeline: ingest, clean, score, detect, recommend, load SQL.

    Returns a dict of row counts for each generated output.
    """
    from src.pipeline import run_pipeline

    outputs = run_pipeline(raw_dir, output_dir)
    counts: dict[str, int] = {name: len(frame) for name, frame in outputs.items()}

    sql_counts = load_to_sql(output_dir, db_path)
    counts.update(sql_counts)

    metrics_path = Path(output_dir) / "seller_metrics.csv"
    if metrics_path.is_file():
        metrics = pd.read_csv(metrics_path)
        report = recommend_actions(metrics)
        report_path = Path(output_dir) / "seller_report.csv"
        report.to_csv(report_path, index=False)
        counts["seller_report"] = len(report)

    return counts
