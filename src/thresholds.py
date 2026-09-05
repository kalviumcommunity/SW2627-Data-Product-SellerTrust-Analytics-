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

SEGMENT_LABELS = (
    "High-Risk",
    "Return-Prone",
    "Inconsistent",
    "Reliable",
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
        cutoffs[metric] = {str(level): float(quantiles.loc[level]) for level in percentile_levels}
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


def compute_trust_score_distribution(trust_scores: pd.Series) -> dict[str, object]:
    """Compute descriptive distribution statistics for trust scores."""
    numeric_scores = pd.to_numeric(trust_scores, errors="coerce").dropna()
    if numeric_scores.empty:
        raise ValueError("trust_scores must contain at least one numeric value.")

    quartiles = numeric_scores.quantile([0.25, 0.5, 0.75])
    return {
        "mean": round(float(numeric_scores.mean()), 2),
        "median": round(float(quartiles.loc[0.5]), 2),
        "std": round(float(numeric_scores.std(ddof=0)), 2),
        "quartile_breaks": {
            "q1": round(float(quartiles.loc[0.25]), 2),
            "q2": round(float(quartiles.loc[0.5]), 2),
            "q3": round(float(quartiles.loc[0.75]), 2),
        },
    }


def _segment_sizes(trust_scores: pd.Series, thresholds: Iterable[float]) -> pd.Series:
    values = pd.to_numeric(trust_scores, errors="coerce").dropna()
    if values.empty:
        raise ValueError("trust_scores must contain at least one numeric value.")

    ordered_thresholds = sorted(float(value) for value in thresholds)
    if len(ordered_thresholds) != 3:
        raise ValueError("thresholds must include exactly three values.")

    segments = pd.cut(
        values,
        bins=[float("-inf"), *ordered_thresholds, float("inf")],
        labels=SEGMENT_LABELS,
        include_lowest=True,
    )
    counts = segments.value_counts(normalize=True).reindex(SEGMENT_LABELS, fill_value=0.0)
    return counts


def validate_segmentation_thresholds(
    trust_scores: pd.Series,
    thresholds: Iterable[float],
    min_share: float = 0.05,
) -> dict[str, object]:
    """Validate tier balance and adjust to quartiles when a tier is too small."""
    if not 0 < min_share < 0.25:
        raise ValueError("min_share must be > 0 and < 0.25.")

    tier_shares = _segment_sizes(trust_scores, thresholds)
    is_balanced = bool((tier_shares >= min_share).all())

    adjusted_thresholds = sorted(float(value) for value in thresholds)
    if not is_balanced:
        numeric_scores = pd.to_numeric(trust_scores, errors="coerce").dropna()
        quartiles = numeric_scores.quantile([0.25, 0.5, 0.75])
        adjusted_thresholds = [float(quartiles.loc[q]) for q in (0.25, 0.5, 0.75)]
        tier_shares = _segment_sizes(numeric_scores, adjusted_thresholds)
        is_balanced = bool((tier_shares >= min_share).all())

    return {
        "is_balanced": is_balanced,
        "min_share": min_share,
        "thresholds": adjusted_thresholds,
        "tier_shares": {tier: round(float(share), 4) for tier, share in tier_shares.items()},
    }
