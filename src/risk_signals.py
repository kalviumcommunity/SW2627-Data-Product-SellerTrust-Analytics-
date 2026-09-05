"""Risk signal decomposition: breaks down trust score into per-signal contributions."""

from __future__ import annotations

import pandas as pd

from src.trust_score import WEIGHTS, _normalise_0_100, _score_review_quality


def decompose_risk_signals(seller_metrics: pd.DataFrame) -> pd.DataFrame:
    """Decompose trust score into individual signal contributions per seller.

    For each seller, computes:
        - Raw score (0-100) for each signal
        - Weighted contribution of each signal to the final trust score
        - Which signal contributes most to a seller being risky

    Returns a DataFrame with columns:
        - seller_id
        - trust_score
        - delivery_raw, review_raw, cancellation_raw, negative_review_raw (0-100)
        - delivery_contribution, review_contribution, cancellation_contribution,
          negative_review_contribution (weighted contribution to trust score)
        - weakest_signal: the signal with lowest raw score (biggest drag)
    """
    scored = seller_metrics.copy()

    delivery_raw = _normalise_0_100(1 - scored["late_delivery_rate"], invert=False)
    review_raw = _score_review_quality(scored["average_review_score"])
    cancellation_raw = _normalise_0_100(scored["cancellation_rate_proxy"], invert=True)
    negative_review_raw = _normalise_0_100(scored["negative_review_rate"], invert=True)

    delivery_contribution = (WEIGHTS["delivery_performance"] * delivery_raw).round(2)
    review_contribution = (WEIGHTS["review_quality"] * review_raw).round(2)
    cancellation_contribution = (WEIGHTS["cancellation_score"] * cancellation_raw).round(2)
    negative_review_contribution = (WEIGHTS["negative_review_score"] * negative_review_raw).round(2)

    trust_score = (
        delivery_contribution + review_contribution + cancellation_contribution + negative_review_contribution
    ).round(2)

    signal_raw = pd.DataFrame(
        {
            "delivery": delivery_raw,
            "review": review_raw,
            "cancellation": cancellation_raw,
            "negative_review": negative_review_raw,
        }
    )
    weakest_signal = signal_raw.idxmin(axis=1)

    result = pd.DataFrame(
        {
            "seller_id": scored["seller_id"],
            "trust_score": pd.to_numeric(trust_score, errors="coerce").round(2),
            "delivery_raw": delivery_raw.round(2),
            "review_raw": review_raw.round(2),
            "cancellation_raw": cancellation_raw.round(2),
            "negative_review_raw": negative_review_raw.round(2),
            "delivery_contribution": delivery_contribution,
            "review_contribution": review_contribution,
            "cancellation_contribution": cancellation_contribution,
            "negative_review_contribution": negative_review_contribution,
            "weakest_signal": weakest_signal,
        }
    )

    result.loc[~scored["eligible_for_risk_score"], "trust_score"] = pd.NA

    return result
