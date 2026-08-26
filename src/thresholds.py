"""Derive statistical score-normalisation thresholds from seller metric data.

The functions in this module compute distribution-aware cutoffs from observed
seller metrics instead of relying on hardcoded constants. We use empirical
percentiles so thresholds adapt automatically as the seller population shifts.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


RISK_METRICS = (
    "late_delivery_rate",
    "average_review_score",
    "cancellation_rate_proxy",
    "negative_review_rate",
)


def _resolve_metrics(
    seller_metrics: pd.DataFrame,
    metric_columns: Iterable[str] | None = None,
) -> list[str]:
    metrics = list(metric_columns or RISK_METRICS)
    missing = [column for column in metrics if column not in seller_metrics.columns]
    if missing:
        raise ValueError(f"Missing metric columns: {', '.join(missing)}")
    return metrics


def compute_percentile_ranks(
    seller_metrics: pd.DataFrame,
    metric_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Compute seller-level percentile ranks for each risk metric.

    Percentile rank is an empirical CDF estimate:
    rank(value) / N where N is the number of sellers with non-null values.
    """
    metrics = _resolve_metrics(seller_metrics, metric_columns)
    ranks = pd.DataFrame(index=seller_metrics.index)
    for metric in metrics:
        ranks[f"{metric}_percentile"] = seller_metrics[metric].rank(
            method="average",
            pct=True,
            na_option="keep",
        )
    return ranks


def derive_percentile_cutoffs(
    seller_metrics: pd.DataFrame,
    metric_columns: Iterable[str] | None = None,
    percentiles: Iterable[float] = (0.5, 0.75, 0.9),
) -> dict[str, dict[str, float]]:
    """Return metric cutoffs at requested percentile levels.

    Quantile interpolation follows pandas defaults, yielding reproducible
    cutoffs directly from observed seller distributions.
    """
    metrics = _resolve_metrics(seller_metrics, metric_columns)
    percentile_levels = [float(value) for value in percentiles]
    for value in percentile_levels:
        if not 0 <= value <= 1:
            raise ValueError("Percentiles must be between 0 and 1.")

    cutoffs: dict[str, dict[str, float]] = {}
    for metric in metrics:
        quantiles = seller_metrics[metric].quantile(percentile_levels)
        cutoffs[metric] = {
            str(level): float(quantiles.loc[level]) for level in percentile_levels
        }
    return cutoffs


def build_threshold_config(
    seller_metrics: pd.DataFrame,
    metric_columns: Iterable[str] | None = None,
    percentiles: Iterable[float] = (0.5, 0.75, 0.9),
) -> dict[str, object]:
    """Build trust-score threshold configuration from seller data."""
    metrics = _resolve_metrics(seller_metrics, metric_columns)
    percentile_levels = [float(value) for value in percentiles]
    return {
        "strategy": "percentile",
        "metric_columns": metrics,
        "percentiles": percentile_levels,
        "cutoffs": derive_percentile_cutoffs(
            seller_metrics=seller_metrics,
            metric_columns=metrics,
            percentiles=percentile_levels,
        ),
    }
