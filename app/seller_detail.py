from __future__ import annotations

from io import StringIO

import pandas as pd

from src.actions import recommend_actions
from src.anomaly_detection import compute_seller_anomalies
from src.risk_signals import decompose_risk_signals
from src.seller_report import build_history_chart, collect_seller_report, render_report
from src.trend_detection import compute_seller_review_trends


def build_seller_detail(metrics: pd.DataFrame, fact: pd.DataFrame, seller_id: str) -> dict:
    """Assemble all dashboard and download data for one seller."""
    matched = metrics[metrics["seller_id"].astype(str) == str(seller_id)]
    if matched.empty:
        raise ValueError(f"Seller {seller_id!r} is not available in the current dataset.")
    seller_metrics = matched.copy()
    seller_fact = fact[fact["seller_id"].astype(str) == str(seller_id)].copy()
    actions = recommend_actions(seller_metrics)
    anomalies = compute_seller_anomalies(seller_metrics)
    trends = compute_seller_review_trends(seller_fact) if not seller_fact.empty else None
    report = collect_seller_report(
        str(seller_id),
        seller_metrics,
        seller_fact,
        trends=trends,
        anomalies=anomalies,
        actions=actions,
    )
    signals = decompose_risk_signals(seller_metrics)
    return {
        "report": report,
        "signals": signals,
        "chart_html": build_history_chart(report["history"], str(seller_id)),
        "html": render_report(report),
    }


def seller_detail_csv(detail: dict) -> bytes:
    """Serialize the seller detail metrics and action into a downloadable CSV."""
    report = detail["report"]
    row = {metric["key"]: metric["value"] for metric in report["metrics"]}
    row.update(
        {
            "seller_id": report["seller_id"],
            "risk_tier": report["risk_tier"],
            "recommended_action": report["recommended_action"],
            "evidence": " | ".join(report["evidence"]),
        }
    )
    buffer = StringIO()
    pd.DataFrame([row]).to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")
