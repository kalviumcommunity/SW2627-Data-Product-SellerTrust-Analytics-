from __future__ import annotations

import pandas as pd

from src.anomaly_detection import compute_seller_anomalies

METRICS_TO_CHECK = [
    "late_delivery_rate",
    "average_review_score",
    "cancellation_rate_proxy",
    "negative_review_rate",
    "average_response_time_hours",
]


BADGE_BY_TIER = {
    "High-Risk": "🔴 High Risk",
    "Return-Prone": "🟡 Watchlist",
    "Inconsistent": "🟡 Watchlist",
    "Reliable": "🟢 Trusted",
    "Insufficient Data": "⚪ Insufficient Data",
}

METRIC_LABELS = {
    "late_delivery_rate": "Late delivery rate",
    "average_review_score": "Average review score",
    "negative_review_rate": "Negative review rate",
    "cancellation_rate_proxy": "Return rate proxy",
    "average_response_time_hours": "Response time",
}


def add_alert_badges(metrics: pd.DataFrame) -> pd.DataFrame:
    """Add scorecard-friendly alert badge and anomaly summary columns."""
    scorecard = metrics.copy()
    anomalies = compute_seller_anomalies(scorecard)
    anomaly_cols = ["seller_id"] + [c for c in anomalies.columns if c not in scorecard.columns]
    scorecard = scorecard.merge(
        anomalies[anomaly_cols],
        on="seller_id",
        how="left",
    )
    scorecard["any_anomaly"] = scorecard["any_anomaly"].fillna(False).astype(bool)
    scorecard["anomaly_count"] = scorecard["anomaly_count"].fillna(0).astype(int)
    scorecard["alert_badge"] = scorecard["risk_tier"].map(BADGE_BY_TIER).fillna(
        "⚪ Unclassified"
    )
    scorecard.loc[scorecard["any_anomaly"], "alert_badge"] = (
        "🔴 Anomaly: " + scorecard.loc[scorecard["any_anomaly"], "risk_tier"].astype(str)
    )
    return scorecard


def _seller_monthly_peaks(order_fact: pd.DataFrame, seller_id: str) -> dict[str, str]:
    if order_fact.empty:
        return {}

    fact = order_fact[order_fact["seller_id"] == seller_id].copy()
    if fact.empty:
        return {}

    fact["purchase_month"] = fact["purchase_month"].fillna(
        pd.to_datetime(
            fact["order_purchase_timestamp"],
            errors="coerce",
        ).dt.to_period("M").astype("string")
    )
    fact["review_score"] = pd.to_numeric(fact["review_score"], errors="coerce")
    fact["is_late_delivery"] = pd.to_numeric(
        fact["is_late_delivery"], errors="coerce"
    ).fillna(0)
    fact["response_time_hours"] = pd.to_numeric(
        fact["response_time_hours"], errors="coerce"
    )

    monthly = fact.groupby("purchase_month", as_index=False).agg(
        late_delivery_rate=("is_late_delivery", "mean"),
        average_review_score=("review_score", "mean"),
        negative_review_rate=(
            "review_score",
            lambda values: float(values.dropna().le(2).mean())
            if values.notna().any()
            else 0.0,
        ),
        cancellation_rate_proxy=(
            "order_status",
            lambda values: float(values.astype("string").str.lower().eq("canceled").mean()),
        ),
        average_response_time_hours=("response_time_hours", "mean"),
    )
    peaks: dict[str, str] = {}
    for metric in METRICS_TO_CHECK:
        if metric not in monthly or monthly[metric].dropna().empty:
            continue
        if metric == "average_review_score":
            row = monthly.loc[monthly[metric].idxmin()]
        else:
            row = monthly.loc[monthly[metric].idxmax()]
        peaks[metric] = str(row["purchase_month"])
    return peaks


def build_anomaly_detail_rows(
    scorecard: pd.DataFrame,
    order_fact: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Create expandable anomaly detail rows with metric labels and timestamps."""
    rows: list[dict[str, str | int | float]] = []
    history = order_fact if order_fact is not None else pd.DataFrame()

    for _, seller in scorecard[scorecard["any_anomaly"]].iterrows():
        anomaly_cols = [c for c in scorecard.columns if c.endswith("_anomaly") and c != "any_anomaly"]
        metrics = [
            c.replace("_anomaly", "")
            for c in anomaly_cols
            if seller.get(c, False)
        ]
        peaks = _seller_monthly_peaks(history, seller["seller_id"])
        for metric in metrics:
            value = seller.get(metric, pd.NA)
            rows.append(
                {
                    "seller_id": seller["seller_id"],
                    "anomaly_type": METRIC_LABELS.get(metric, metric),
                    "spike_timestamp": peaks.get(metric, "Latest seller metrics"),
                    "metric_value": round(float(value), 3) if pd.notna(value) else pd.NA,
                    "risk_tier": seller["risk_tier"],
                    "alert_badge": seller["alert_badge"],
                }
            )

    return pd.DataFrame(rows)
