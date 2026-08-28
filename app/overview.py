from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.trust_score import calculate_trust_score


DEFAULT_SELLER_METRICS_PATH = Path("data/processed/seller_metrics.csv")
AT_RISK_TRUST_SCORE_THRESHOLD = 60.0


def _as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype("string").str.lower().isin(["true", "1", "yes"])


def load_seller_metrics(path: str | Path = DEFAULT_SELLER_METRICS_PATH) -> pd.DataFrame:
    """Load dashboard-ready seller metrics from the processed CSV output."""
    metrics_path = Path(path)
    if not metrics_path.is_file():
        raise FileNotFoundError(f"seller metrics file not found: {metrics_path}")
    return pd.read_csv(metrics_path)


def prepare_seller_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    """Ensure seller metrics include the trust score needed by overview cards."""
    prepared = metrics.copy()
    if "trust_score" not in prepared.columns:
        prepared = calculate_trust_score(prepared)
    return prepared


def build_overview_kpis(metrics: pd.DataFrame) -> dict[str, float | int]:
    """Summarise seller-level metrics for the Trust Overview KPI cards."""
    prepared = prepare_seller_metrics(metrics)
    eligible = prepared[_as_bool(prepared["eligible_for_risk_score"])]

    return {
        "avg_trust_score": round(float(eligible["trust_score"].mean()), 1),
        "return_rate_pct": round(float(eligible["cancellation_rate_proxy"].mean() * 100), 1),
        "negative_sentiment_pct": round(float(eligible["negative_review_rate"].mean() * 100), 1),
        "at_risk_sellers_count": int(
            eligible["trust_score"].lt(AT_RISK_TRUST_SCORE_THRESHOLD).sum()
        ),
    }
