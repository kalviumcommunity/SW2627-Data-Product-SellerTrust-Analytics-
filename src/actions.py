"""Action recommendation engine: maps seller risk signals to recommended actions."""

from __future__ import annotations

import pandas as pd

from src.anomaly_detection import compute_seller_anomalies
from src.config_loader import get_config
from src.taxonomy import add_canonical_risk_tier
from src.trust_score import calculate_trust_score

ACTION_ESCALATE = "Escalate"
ACTION_COACH = "Coach"
ACTION_MONITOR = "Monitor"
ACTION_NONE = "No Action"


def _get_thresholds() -> dict[str, float]:
    """Load action thresholds from config."""
    cfg = get_config()
    return cfg.get(
        "action_thresholds",
        {
            "escalate_score": 45,
            "coach_score": 65,
            "monitor_score": 80,
            "escalate_anomaly_count": 3,
        },
    )


def _get_signal_thresholds() -> dict[str, dict[str, float]]:
    """Load configured signal thresholds used to explain action decisions."""
    return get_config().get("action_tiers", {})


def _build_evidence(row: pd.Series) -> list[str]:
    """Generate human-readable evidence bullets for a seller's risk profile."""
    evidence = []
    thresholds = _get_thresholds()
    signal_thresholds = _get_signal_thresholds()
    escalate = signal_thresholds.get("escalate", {})
    coach = signal_thresholds.get("coach", {})

    delivered_count = row.get("delivered_orders_with_dates")
    if pd.notna(delivered_count) and delivered_count == 0:
        evidence.append("No delivered orders with valid delivery dates; delivery rate is unknown")

    if row.get("late_delivery_rate", 0) > escalate.get("late_delivery_rate", 0.15):
        evidence.append(f"Late delivery rate is {row['late_delivery_rate']:.0%} (high)")
    elif row.get("late_delivery_rate", 0) > coach.get("late_delivery_rate", 0.05):
        evidence.append(f"Late delivery rate is {row['late_delivery_rate']:.0%}")

    if row.get("average_review_score", 5) < 3.0:
        evidence.append(f"Average review score is {row['average_review_score']:.1f}/5.0 (very low)")
    elif row.get("average_review_score", 5) < 3.5:
        evidence.append(f"Average review score is {row['average_review_score']:.1f}/5.0")

    if row.get("negative_review_rate", 0) > escalate.get("negative_review_rate", 0.25):
        evidence.append(f"Negative review rate is {row['negative_review_rate']:.0%} (high)")
    elif row.get("negative_review_rate", 0) > coach.get("negative_review_rate", 0.15):
        evidence.append(f"Negative review rate is {row['negative_review_rate']:.0%}")

    if row.get("cancellation_rate_proxy", 0) > escalate.get("cancellation_rate_proxy", 0.025):
        evidence.append(f"Cancellation rate is {row['cancellation_rate_proxy']:.0%} (elevated)")
    elif row.get("cancellation_rate_proxy", 0) > coach.get("cancellation_rate_proxy", 0.0125):
        evidence.append(f"Cancellation rate is {row['cancellation_rate_proxy']:.0%}")

    if row.get("average_response_time_hours", 0) > 100:
        evidence.append(f"Avg response time is {row['average_response_time_hours']:.0f}h (slow)")

    anomaly_count = row.get("anomaly_count", 0)
    if anomaly_count >= thresholds["escalate_anomaly_count"]:
        evidence.append(f"{anomaly_count} metrics flagged as anomalous")
    elif anomaly_count > 0:
        evidence.append(f"{anomaly_count} metric(s) flagged as anomalous")

    if not evidence:
        evidence.append("No significant risk signals detected")

    return evidence


def _build_action_detail(row: pd.Series) -> dict[str, str | float | int | None]:
    """Return a primary driver with its value, denominator, and next step."""
    signal_thresholds = _get_signal_thresholds()
    escalate = signal_thresholds.get("escalate", {})
    coach = signal_thresholds.get("coach", {})
    candidates = [
        (
            "Late delivery rate",
            "late_delivery_rate",
            escalate.get("late_delivery_rate", 0.1),
            "delivered_orders_with_dates",
        ),
        ("Negative review rate", "negative_review_rate", escalate.get("negative_review_rate", 0.25), "review_count"),
        (
            "Cancellation rate proxy",
            "cancellation_rate_proxy",
            escalate.get("cancellation_rate_proxy", 0.025),
            "total_orders",
        ),
        ("Average review score", "average_review_score", coach.get("average_review_score", 3.8), "review_count"),
    ]
    breached = []
    for label, column, threshold, denominator_column in candidates:
        value = row.get(column)
        if pd.isna(value):
            continue
        is_low_review = column == "average_review_score"
        if (is_low_review and value < threshold) or (not is_low_review and value > threshold):
            severity = abs(float(value) - threshold)
            breached.append((severity, label, column, denominator_column, value))

    if not breached:
        return {
            "primary_driver": "No significant risk signal",
            "metric_value": None,
            "denominator": None,
            "explanation": "No configured signal threshold was breached.",
            "recommended_next_step": "Continue routine monitoring.",
        }

    _, label, column, denominator_column, value = max(breached, key=lambda item: item[0])
    denominator = row.get(denominator_column)
    if pd.isna(denominator):
        denominator = None
    action = row.get("recommended_action", ACTION_MONITOR)
    next_steps = {
        ACTION_ESCALATE: "Escalate to marketplace operations for review.",
        ACTION_COACH: "Contact the seller with targeted coaching guidance.",
        ACTION_MONITOR: "Monitor the next review period for improvement.",
        ACTION_NONE: "No intervention is required.",
    }
    return {
        "primary_driver": label,
        "metric_value": float(value),
        "denominator": int(denominator) if denominator is not None else None,
        "explanation": f"{label} breached its configured action threshold.",
        "recommended_next_step": next_steps.get(action, "Review the seller profile."),
    }


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
    thresholds = _get_thresholds()

    if trust_score is None or pd.isna(trust_score):
        return ACTION_MONITOR

    if trust_score < thresholds["escalate_score"]:
        return ACTION_ESCALATE

    if trust_score < thresholds["coach_score"] and anomaly_count >= thresholds["escalate_anomaly_count"]:
        return ACTION_ESCALATE

    if trust_score < thresholds["coach_score"]:
        return ACTION_COACH

    if negative_review_rate > 0.25 or cancellation_rate > 0.03:
        return ACTION_COACH

    if trust_score < thresholds["monitor_score"]:
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
    if "delivered_orders_with_dates" not in prepared.columns:
        prepared["delivered_orders_with_dates"] = pd.NA
    if "review_count" not in prepared.columns:
        prepared["review_count"] = pd.NA
    prepared["eligible_for_risk_score"] = prepared["eligible_for_risk_score"].astype(bool)
    scored = calculate_trust_score(prepared)
    anomalies = compute_seller_anomalies(prepared)
    merged = scored.merge(
        anomalies[["seller_id", "any_anomaly", "anomaly_count"]],
        on="seller_id",
        how="left",
        suffixes=("", "_anomaly"),
    )
    merged["anomaly_count"] = merged["anomaly_count"].fillna(0).astype(int)
    merged["is_anomaly"] = merged["any_anomaly"].fillna(False).astype(bool)

    merged = add_canonical_risk_tier(merged)

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
    details = merged.apply(_build_action_detail, axis=1, result_type="expand")
    merged = pd.concat([merged, details], axis=1)

    return merged[
        [
            "seller_id",
            "trust_score",
            "risk_tier",
            "recommended_action",
            "evidence",
            "anomaly_count",
            "total_orders",
            "delivered_orders_with_dates",
            "late_delivery_rate",
            "average_review_score",
            "negative_review_rate",
            "cancellation_rate_proxy",
            "average_response_time_hours",
            "review_count",
            "primary_driver",
            "metric_value",
            "denominator",
            "explanation",
            "recommended_next_step",
        ]
    ]
