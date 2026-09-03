from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.overview import prepare_seller_metrics


SEGMENT_ORDER = ["Reliable", "Inconsistent", "Return-Prone", "High-Risk"]
SEGMENT_COLORS = {
    "Reliable": "#2ca02c",
    "Inconsistent": "#1f77b4",
    "Return-Prone": "#ffbf00",
    "High-Risk": "#d62728",
}


def prepare_segment_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    """Prepare seller metrics with risk tiers for the Behaviour Segments tab."""
    prepared = prepare_seller_metrics(metrics)
    if "risk_tier" not in prepared.columns:
        prepared["risk_tier"] = pd.cut(
            prepared["trust_score"],
            bins=[-0.01, 45, 60, 75, 100],
            labels=["High-Risk", "Return-Prone", "Inconsistent", "Reliable"],
        ).astype("string")
        prepared.loc[prepared["trust_score"].isna(), "risk_tier"] = "Insufficient Data"
    return prepared[prepared["risk_tier"].isin(SEGMENT_ORDER)].copy()


def build_segment_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    """Summarise seller behaviour tiers for the portfolio segment view."""
    prepared = prepare_segment_metrics(metrics)
    summary = (
        prepared.groupby("risk_tier", observed=True)
        .agg(
            sellers=("seller_id", "nunique"),
            avg_trust_score=("trust_score", "mean"),
            avg_return_rate=("cancellation_rate_proxy", "mean"),
            avg_negative_sentiment=("negative_review_rate", "mean"),
            avg_late_delivery_rate=("late_delivery_rate", "mean"),
        )
        .reindex(SEGMENT_ORDER)
        .reset_index()
    )
    summary["sellers"] = summary["sellers"].fillna(0).astype(int)
    for column in ["avg_return_rate", "avg_negative_sentiment", "avg_late_delivery_rate"]:
        summary[column] = (summary[column] * 100).round(1)
    summary["avg_trust_score"] = summary["avg_trust_score"].round(1)
    return summary


def build_segment_composition_chart(metrics: pd.DataFrame) -> go.Figure:
    """Build the tier composition chart for Behaviour Segments."""
    summary = build_segment_summary(metrics)
    fig = px.bar(
        summary,
        x="risk_tier",
        y="sellers",
        color="risk_tier",
        color_discrete_map=SEGMENT_COLORS,
        category_orders={"risk_tier": SEGMENT_ORDER},
        hover_data={
            "sellers": True,
            "avg_trust_score": ":.1f",
            "avg_return_rate": ":.1f",
            "avg_negative_sentiment": ":.1f",
            "avg_late_delivery_rate": ":.1f",
        },
        labels={
            "risk_tier": "Behaviour Segment",
            "sellers": "Seller Count",
            "avg_trust_score": "Avg Trust Score",
            "avg_return_rate": "Avg Return Rate %",
            "avg_negative_sentiment": "Avg Negative Sentiment %",
            "avg_late_delivery_rate": "Avg Late Delivery %",
        },
        title="Seller Behaviour Segment Composition",
    )
    fig.update_layout(
        height=420,
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
        showlegend=False,
    )
    return fig
