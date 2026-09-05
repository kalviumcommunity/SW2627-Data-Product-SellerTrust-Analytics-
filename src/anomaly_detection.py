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
    threshold: float = 3.5,
) -> pd.Series:
    """
    Detect anomalies using Z-score method.

    Args:
        series: Numeric series to check for anomalies
        threshold: Z-score threshold (default 3.5, raised from 3.0 after manual
            validation — see docs/anomaly-validation.md — to reduce false-positive rate)

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
    zscore_threshold: float = 3.5,
    min_orders: int = 5,
    exclude_early_deliveries: bool = True,
) -> pd.DataFrame:
    """
    Compute anomaly flags for each seller across specified metrics.

    Args:
        seller_metrics: DataFrame with seller-level metrics
        metrics: List of metric columns to check (default: risk metrics)
        iqr_multiplier: IQR multiplier for outlier detection
        zscore_threshold: Z-score threshold for anomaly detection (default 3.5)
        min_orders: Minimum order count required before applying Z-score detection.
            Sellers below this threshold are excluded from Z-score flags only;
            IQR flags still apply.  Set to 0 to disable.
        exclude_early_deliveries: If True, negative ``average_delivery_delay_days``
            values (early deliveries) are not flagged as anomalies — they represent
            good performance, not risk.

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

    # Pre-compute the mask for sellers with insufficient order history
    insufficient_orders = pd.Series(False, index=seller_metrics.index)
    if min_orders > 0 and "total_orders" in seller_metrics.columns:
        order_counts = pd.to_numeric(seller_metrics["total_orders"], errors="coerce").fillna(0)
        insufficient_orders = order_counts < min_orders

    results = pd.DataFrame(index=seller_metrics.index)
    results["seller_id"] = seller_metrics["seller_id"]

    for metric in available_metrics:
        # IQR-based outlier detection
        iqr_outliers = detect_iqr_outliers(seller_metrics[metric], multiplier=iqr_multiplier)

        # Z-score based anomaly detection
        zscore_anomalies = detect_zscore_anomalies(seller_metrics[metric], threshold=zscore_threshold)

        # Suppress Z-score flags for sellers without enough orders
        if min_orders > 0:
            zscore_anomalies = zscore_anomalies & ~insufficient_orders

        # For delivery delay, don't flag negative values (early = good, not risky)
        if exclude_early_deliveries and metric == "average_delivery_delay_days":
            delay = pd.to_numeric(seller_metrics[metric], errors="coerce")
            early_delivery_mask = delay < 0
            iqr_outliers = iqr_outliers & ~early_delivery_mask
            zscore_anomalies = zscore_anomalies & ~early_delivery_mask

        results[f"{metric}_iqr_outlier"] = iqr_outliers
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
    zscore_threshold: float = 3.5,
    min_orders: int = 5,
    exclude_early_deliveries: bool = True,
) -> pd.DataFrame:
    """
    Run anomaly detection on seller metrics and save results.

    Args:
        input_path: Path to seller_metrics.csv
        output_path: Path to output seller_anomalies.csv
        metrics: List of metric columns to check
        iqr_multiplier: IQR multiplier for outlier detection
        zscore_threshold: Z-score threshold for anomaly detection
        min_orders: Minimum orders before Z-score is applied (default 5)
        exclude_early_deliveries: Whether to suppress flags for negative delivery delay

    Returns:
        DataFrame with anomaly results
    """
    seller_metrics = pd.read_csv(input_path)
    anomalies = compute_seller_anomalies(
        seller_metrics,
        metrics=metrics,
        iqr_multiplier=iqr_multiplier,
        zscore_threshold=zscore_threshold,
        min_orders=min_orders,
        exclude_early_deliveries=exclude_early_deliveries,
    )
    anomalies.to_csv(output_path, index=False)
    return anomalies
