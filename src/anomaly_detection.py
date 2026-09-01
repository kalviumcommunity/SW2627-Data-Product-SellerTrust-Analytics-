"""Anomaly detection for seller behaviour spikes using IQR and Z-score methods."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import numpy as np


METRICS_TO_CHECK = [
    "late_delivery_rate",
    "average_review_score",
    "negative_review_rate",
    "cancellation_rate_proxy",
    "average_response_time_hours",
]

# Direction for each metric: "high" means anomaly is unusually high value,
# "low" means anomaly is unusually low value (e.g., review score dropping).
METRIC_DIRECTIONS = {
    "late_delivery_rate": "high",
    "average_review_score": "low",
    "negative_review_rate": "high",
    "cancellation_rate_proxy": "high",
    "average_response_time_hours": "high",
}


@dataclass(frozen=True)
class AnomalyResult:
    """Single metric anomaly flag with method details."""

    metric: str
    method: str
    threshold: float
    is_anomaly: bool
    value: float


def detect_iqr_outliers(
    series: pd.Series,
    multiplier: float = 1.5,
) -> pd.Series:
    """Flag IQR outliers in a numeric series. Returns boolean Series."""
    values = pd.to_numeric(series, errors="coerce")
    q1, q3 = values.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return (values.lt(lower) | values.gt(upper)).astype("boolean")


def detect_z_score_outliers(
    series: pd.Series,
    threshold: float = 3.0,
) -> pd.Series:
    """Flag Z-score outliers in a numeric series. Returns boolean Series."""
    values = pd.to_numeric(series, errors="coerce")
    mean = values.mean()
    std = values.std()
    if std == 0 or pd.isna(std):
        return pd.Series(False, index=series.index).astype("boolean")
    z_scores = (values - mean).abs() / std
    return z_scores.gt(threshold).astype("boolean")


def detect_anomalies(
    seller_metrics: pd.DataFrame,
    z_threshold: float = 3.0,
    iqr_multiplier: float = 1.5,
) -> pd.DataFrame:
    """Detect anomalous seller metrics using both IQR and Z-score methods.

    A seller is flagged as anomalous if ANY of their metrics is flagged by
    EITHER method. Each metric is checked in its natural direction (e.g.,
    high late_delivery_rate is bad, low average_review_score is bad).

    Returns a DataFrame with one row per seller and columns:
        - seller_id
        - is_anomaly (bool): True if any metric is anomalous
        - anomaly_count (int): number of metrics flagged
        - anomalous_metrics (str): comma-separated list of flagged metrics
        - {metric}_iqr (bool): IQR flag per metric
        - {metric}_zscore (bool): Z-score flag per metric
    """
    eligible = seller_metrics[seller_metrics["eligible_for_risk_score"]].copy()
    result = eligible[["seller_id"]].copy()
    result["is_anomaly"] = False
    result["anomaly_count"] = 0
    result["anomalous_metrics"] = ""

    flagged_counts = pd.Series(0, index=result.index)
    flagged_metrics: list[pd.Series] = []

    for metric in METRICS_TO_CHECK:
        if metric not in eligible.columns:
            continue

        iqr_flags = detect_iqr_outliers(eligible[metric], multiplier=iqr_multiplier)
        z_flags = detect_z_score_outliers(eligible[metric], threshold=z_threshold)

        either_flag = (iqr_flags.fillna(False) | z_flags.fillna(False)).astype(bool)
        flagged_counts += either_flag.astype(int)
        flagged_metrics.append(either_flag)

        result[f"{metric}_iqr"] = iqr_flags
        result[f"{metric}_zscore"] = z_flags

    if flagged_metrics:
        any_flag = flagged_metrics[0].copy()
        for flags in flagged_metrics[1:]:
            any_flag = any_flag | flags
        result["is_anomaly"] = any_flag.astype(bool)

    result["anomaly_count"] = flagged_counts

    metric_names = [m for m in METRICS_TO_CHECK if m in eligible.columns]
    result["anomalous_metrics"] = _build_metric_labels(result, metric_names)

    return result


def _build_metric_labels(
    flagged_df: pd.DataFrame, metrics: list[str]
) -> pd.Series:
    """Build comma-separated labels of anomalous metrics per seller."""
    labels = pd.Series("", index=flagged_df.index)
    for metric in metrics:
        col = f"{metric}_iqr"
        if col in flagged_df.columns:
            mask = flagged_df[col].fillna(False).astype(bool)
            labels[mask] = labels[mask].where(~mask, labels[mask] + ", ") + metric
    return labels.str.strip(", ")


def build_anomaly_summary(anomalies: pd.DataFrame) -> pd.DataFrame:
    """Summarize anomaly counts by metric for reporting."""
    summary_rows = []
    for metric in METRICS_TO_CHECK:
        iqr_col = f"{metric}_iqr"
        z_col = f"{metric}_zscore"
        if iqr_col not in anomalies.columns:
            continue
        iqr_count = anomalies[iqr_col].fillna(False).sum()
        z_count = anomalies[z_col].fillna(False).sum()
        either_count = (anomalies[iqr_col].fillna(False) | anomalies[z_col].fillna(False)).sum()
        summary_rows.append({
            "metric": metric,
            "iqr_flagged": int(iqr_count),
            "zscore_flagged": int(z_count),
            "either_flagged": int(either_count),
        })
    return pd.DataFrame(summary_rows)
