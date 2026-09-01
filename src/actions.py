"""Action recommendation engine: maps seller risk signals to recommended actions."""

from __future__ import annotations

import pandas as pd

from src.trust_score import calculate_trust_score
from src.anomaly_detection import detect_anomalies


ACTION_ESCALATE = "Escalate"
ACTION_COACH = "Coach"
ACTION_MONITOR = "Monitor"
ACTION_NONE = "No Action"

# Thresholds for action assignment (trust score 0-100)
ESCALATE_SCORE_THRESHOLD = 45
COACH_SCORE_THRESHOLD = 65

# Minimum anomaly count to trigger Escalate
ESCALATE_ANOMALY_COUNT = 3


def _build_evidence(row: pd.Series) -> list[str]:
    """Generate human-readable evidence bullets for a seller's risk profile."""
    evidence = []

    if row.get("late_delivery_rate", 0) > 0.15:
        evidence.append(f"Late delivery rate is {row['late_delivery_rate']:.0%} (high)")
    elif row.get("late_delivery_rate", 0) > 0.05:
        evidence.append(f"Late delivery rate is {row['late_delivery_rate']:.0%}")

    if row.get("average_review_score", 5) < 3.0:
        evidence.append(f"Average review score is {row['average_review_score']:.1f}/5.0 (very low)")
    elif row.get("average_review_score", 5) < 3.5:
        evidence.append(f"Average review score is {row['average_review_score']:.1f}/5.0")

    if row.get("negative_review_rate", 0) > 0.3:
        evidence.append(f"Negative review rate is {row['negative_review_rate']:.0%} (high)")
    elif row.get("negative_review_rate", 0) > 0.15:
        evidence.append(f"Negative review rate is {row['negative_review_rate']:.0%}")

    if row.get("cancellation_rate_proxy", 0) > 0.05:
        evidence.append(f"Cancellation rate is {row['cancellation_rate_proxy']:.0%} (elevated)")
    elif row.get("cancellation_rate_proxy", 0) > 0:
        evidence.append(f"Cancellation rate is {row['cancellation_rate_proxy']:.0%}")

    if row.get("average_response_time_hours", 0) > 100:
        evidence.append(f"Avg response time is {row['average_response_time_hours']:.0f}h (slow)")

    anomaly_count = row.get("anomaly_count", 0)
    if anomaly_count >= 3:
        evidence.append(f"{anomaly_count} metrics flagged as anomalous")
    elif anomaly_count > 0:
        evidence.append(f"{anomaly_count} metric(s) flagged as anomalous")

    if not evidence:
        evidence.append("No significant risk signals detected")

    return evidence


def _assign_action(
    trust_score: float | None,
    anomaly_count: int,
    negative_review_rate: float,
    cancellation_rate: float,
) -> str:
    """Determine the recommended action for a seller based on their risk profile.

    Escalate: trust score < 45 OR (trust score < 65 AND >= 3 anomalies)
    Coach: trust score < 65 OR has fixable signal issues
    Monitor: trust score between 65-80 with minor concerns
    No Action: trust score >= 80 with no concerns
    """
    if pd.isna(trust_score):
        return ACTION_MONITOR

    if trust_score < ESCALATE_SCORE_THRESHOLD:
        return ACTION_ESCALATE

    if trust_score < COACH_SCORE_THRESHOLD and anomaly_count >= ESCALATE_ANOMALY_COUNT:
        return ACTION_ESCALATE

    if trust_score < COACH_SCORE_THRESHOLD:
        return ACTION_COACH

    if negative_review_rate > 0.25 or cancellation_rate > 0.03:
        return ACTION_COACH

    if trust_score < 80:
        return ACTION_MONITOR

    return ACTION_NONE


def recommend_actions(seller_metrics: pd.DataFrame) -> pd.DataFrame:
    """Generate action recommendations for all eligible sellers.

    Combines trust score, risk tier, and anomaly detection to produce
    a recommended action (Escalate / Coach / Monitor / No Action) per seller
    with supporting evidence bullets.

    Returns a DataFrame with columns:
        - seller_id
        - trust_score
        - risk_tier
        - recommended_action
        - evidence (list of strings)
        - anomaly_count
    """
    prepared = seller_metrics.copy()
    prepared["eligible_for_risk_score"] = prepared["eligible_for_risk_score"].astype(bool)
    scored = calculate_trust_score(prepared)
    anomalies = detect_anomalies(prepared)
    merged = scored.merge(
        anomalies[["seller_id", "is_anomaly", "anomaly_count", "anomalous_metrics"]],
        on="seller_id",
        how="left",
        suffixes=("", "_anomaly"),
    )
    merged["anomaly_count"] = merged["anomaly_count"].fillna(0).astype(int)
    merged["is_anomaly"] = merged["is_anomaly"].fillna(False).astype(bool)

    merged["risk_tier"] = pd.cut(
        merged["trust_score"],
        bins=[-0.01, 45, 65, 80, 100],
        labels=["High-Risk", "Return-Prone", "Inconsistent", "Reliable"],
    ).astype("string")
    merged.loc[merged["trust_score"].isna(), "risk_tier"] = "Insufficient Data"

    merged["recommended_action"] = merged.apply(
        lambda row: _assign_action(
            row["trust_score"],
            row["anomaly_count"],
            row.get("negative_review_rate", 0),
            row.get("cancellation_rate_proxy", 0),
        ),
        axis=1,
    )

    merged["evidence"] = merged.apply(_build_evidence, axis=1)

    return merged[
        [
            "seller_id",
            "trust_score",
            "risk_tier",
            "recommended_action",
            "evidence",
            "anomaly_count",
            "total_orders",
            "late_delivery_rate",
            "average_review_score",
            "negative_review_rate",
            "cancellation_rate_proxy",
            "average_response_time_hours",
        ]
    ]
