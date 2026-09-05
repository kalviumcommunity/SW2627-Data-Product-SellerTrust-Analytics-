"""Anomaly detection for seller behaviour spikes using IQR and Z-score methods."""

from __future__ import annotations

import numpy as np
import pandas as pd


def detect_iqr_outliers(
    series: pd.Series,
    multiplier: float = 1.5,
) -> pd.Series:
    """
    Detect outliers using the Interquartile Range (IQR) method.

    Args:
        series: Numeric series to check for outliers
        multiplier: IQR multiplier (default 1.5 for standard outliers, 3.0 for extreme)

    Returns:
        Boolean series where True indicates an outlier
    """
    numeric = pd.to_numeric(series, errors="coerce")
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1

    if iqr == 0:
        return pd.Series(False, index=series.index)

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    return (numeric < lower_bound) | (numeric > upper_bound)


def detect_zscore_anomalies(
    series: pd.Series,
    threshold: float = 3.0,
) -> pd.Series:
    """
    Detect anomalies using Z-score method.

    Args:
        series: Numeric series to check for anomalies
        threshold: Z-score threshold (default 3.0)

    Returns:
        Boolean series where True indicates an anomaly
    """
    numeric = pd.to_numeric(series, errors="coerce")
    mean = numeric.mean()
    std = numeric.std(ddof=0)

    if std == 0 or pd.isna(std):
        return pd.Series(False, index=series.index)

    z_scores = np.abs((numeric - mean) / std)
    return z_scores > threshold


def compute_seller_anomalies(
    seller_metrics: pd.DataFrame,
    metrics: list[str] | None = None,
    iqr_multiplier: float = 1.5,
    zscore_threshold: float = 3.0,
) -> pd.DataFrame:
    """
    Compute anomaly flags for each seller across specified metrics.

    Args:
        seller_metrics: DataFrame with seller-level metrics
        metrics: List of metric columns to check (default: risk metrics)
        iqr_multiplier: IQR multiplier for outlier detection
        zscore_threshold: Z-score threshold for anomaly detection

    Returns:
        DataFrame with anomaly flags per seller per metric
    """
    if metrics is None:
        metrics = [
            "late_delivery_rate",
            "average_review_score",
            "cancellation_rate_proxy",
            "negative_review_rate",
            "average_delivery_delay_days",
            "average_response_time_hours",
        ]

    # Filter to only metrics that exist in the data
    available_metrics = [m for m in metrics if m in seller_metrics.columns]

    results = pd.DataFrame(index=seller_metrics.index)
    results["seller_id"] = seller_metrics["seller_id"]

    for metric in available_metrics:
        # IQR-based outlier detection
        iqr_outliers = detect_iqr_outliers(seller_metrics[metric], multiplier=iqr_multiplier)
        results[f"{metric}_iqr_outlier"] = iqr_outliers

        # Z-score based anomaly detection
        zscore_anomalies = detect_zscore_anomalies(seller_metrics[metric], threshold=zscore_threshold)
        results[f"{metric}_zscore_anomaly"] = zscore_anomalies

        # Combined flag (either method flags it)
        results[f"{metric}_anomaly"] = iqr_outliers | zscore_anomalies

    # Overall anomaly flag (any metric flagged)
    anomaly_cols = [c for c in results.columns if c.endswith("_anomaly")]
    results["any_anomaly"] = results[anomaly_cols].any(axis=1)

    # Count of anomalous metrics per seller
    results["anomaly_count"] = results[anomaly_cols].sum(axis=1)

    return results.reset_index(drop=True)


def run_anomaly_detection(
    input_path: str,
    output_path: str,
    metrics: list[str] | None = None,
    iqr_multiplier: float = 1.5,
    zscore_threshold: float = 3.0,
) -> pd.DataFrame:
    """
    Run anomaly detection on seller metrics and save results.

    Args:
        input_path: Path to seller_metrics.csv
        output_path: Path to output seller_anomalies.csv
        metrics: List of metric columns to check
        iqr_multiplier: IQR multiplier for outlier detection
        zscore_threshold: Z-score threshold for anomaly detection

    Returns:
        DataFrame with anomaly results
    """
    seller_metrics = pd.read_csv(input_path)
    anomalies = compute_seller_anomalies(
        seller_metrics,
        metrics=metrics,
        iqr_multiplier=iqr_multiplier,
        zscore_threshold=zscore_threshold,
    )
    anomalies.to_csv(output_path, index=False)
    return anomalies
