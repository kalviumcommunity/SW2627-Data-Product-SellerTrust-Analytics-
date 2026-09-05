"""Trust score engine: combines seller metrics into a composite 0-100 trust score."""

from __future__ import annotations

import pandas as pd

# Weights reflect relative importance of each signal.
# Delivery performance and review quality are primary trust indicators (30% each).
# Cancellation and negative review rates are secondary signals (20% each).
# These weights can be adjusted if correlation analysis shows double-counting.
WEIGHTS = {
    "delivery_performance": 0.30,
    "review_quality": 0.30,
    "cancellation_score": 0.20,
    "negative_review_score": 0.20,
}


def _normalise_0_100(series: pd.Series, invert: bool = False) -> pd.Series:
    """Map a 0-1 range series to 0-100. If invert=True, 0 becomes 100 and vice versa."""
    clamped = series.clip(0, 1)
    if invert:
        return (1 - clamped) * 100
    return clamped * 100


def _score_review_quality(avg_review: pd.Series) -> pd.Series:
    """Map average review score (1-5) to 0-100."""
    normalised = (avg_review - 1) / 4
    return normalised.clip(0, 1) * 100


def calculate_trust_score(seller_metrics: pd.DataFrame) -> pd.DataFrame:
    """Compute a composite trust score (0-100) per seller.

    Higher scores indicate more trustworthy sellers. Sellers with fewer than
    5 orders receive a NaN score because their metrics are not statistically
    stable enough to evaluate.

    Scoring breakdown:
        - Delivery Performance (30%): (1 - late_delivery_rate) * 100
        - Review Quality (30%): (avg_review - 1) / 4 * 100
        - Cancellation Score (20%): (1 - cancellation_rate_proxy) * 100
        - Negative Review Score (20%): (1 - negative_review_rate) * 100
    """
    scored = seller_metrics.copy()

    delivery = _normalise_0_100(1 - scored["late_delivery_rate"], invert=False)
    review = _score_review_quality(scored["average_review_score"])
    cancellation = _normalise_0_100(scored["cancellation_rate_proxy"], invert=True)
    negative_review = _normalise_0_100(scored["negative_review_rate"], invert=True)

    raw_score = (
        WEIGHTS["delivery_performance"] * delivery
        + WEIGHTS["review_quality"] * review
        + WEIGHTS["cancellation_score"] * cancellation
        + WEIGHTS["negative_review_score"] * negative_review
    )
    scored["trust_score"] = pd.to_numeric(raw_score, errors="coerce").round(2)

    scored.loc[~scored["eligible_for_risk_score"], "trust_score"] = pd.NA

    return scored
