from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.overview import prepare_seller_metrics


RISK_SIGNAL_COLUMNS = [
    "cancellation_rate_proxy",
    "late_delivery_rate",
    "negative_review_rate",
    "average_response_time_hours",
    "average_review_score",
    "trust_score",
]


def prepare_signal_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    """Return scored, eligible seller metrics for behaviour-signal visuals."""
    prepared = prepare_seller_metrics(metrics)
    eligible = prepared[prepared["eligible_for_risk_score"].astype(bool)].copy()

    for column in RISK_SIGNAL_COLUMNS:
        if column in eligible.columns:
            eligible[column] = pd.to_numeric(eligible[column], errors="coerce")

    return eligible.dropna(subset=["trust_score"])


def build_return_rate_scatter(metrics: pd.DataFrame) -> go.Figure:
    """Build an interactive scatter plot comparing return proxy and trust score."""
    fig = px.scatter(
        metrics,
        x="cancellation_rate_proxy",
        y="trust_score",
        color="risk_tier" if "risk_tier" in metrics.columns else None,
        size="total_orders" if "total_orders" in metrics.columns else None,
        hover_data=[
            column
            for column in [
                "seller_id",
                "total_orders",
                "average_review_score",
                "negative_review_rate",
                "late_delivery_rate",
            ]
            if column in metrics.columns
        ],
        labels={
            "cancellation_rate_proxy": "Return Rate Proxy",
            "trust_score": "Trust Score",
            "risk_tier": "Risk Tier",
            "total_orders": "Total Orders",
            "average_review_score": "Avg Review Score",
            "negative_review_rate": "Negative Sentiment Rate",
            "late_delivery_rate": "Late Delivery Rate",
        },
        title="Return Rate Proxy vs Trust Score",
    )
    fig.update_traces(marker={"opacity": 0.75})
    fig.update_xaxes(tickformat=".0%")
    fig.update_layout(height=440, margin={"l": 20, "r": 20, "t": 60, "b": 20})
    return fig


def build_correlation_heatmap(metrics: pd.DataFrame) -> go.Figure:
    """Build a Plotly heatmap showing correlation between trust risk signals."""
    available_columns = [
        column for column in RISK_SIGNAL_COLUMNS if column in metrics.columns
    ]
    correlations = metrics[available_columns].corr(numeric_only=True)

    fig = px.imshow(
        correlations,
        text_auto=".2f",
        color_continuous_scale="RdBu",
        zmin=-1,
        zmax=1,
        labels={"color": "Correlation"},
        title="Risk Signal Correlation Heatmap",
    )
    fig.update_layout(height=440, margin={"l": 20, "r": 20, "t": 60, "b": 20})
    return fig


def build_cohort_comparison(metrics: pd.DataFrame) -> pd.DataFrame:
    """Summarise high-trust and low-trust seller cohorts for comparison."""
    cohorted = metrics.copy()
    cohorted["trust_cohort"] = pd.cut(
        cohorted["trust_score"],
        bins=[-0.01, 60, 75, 100],
        labels=["Low Trust", "Mid Trust", "High Trust"],
    )
    cohorted = cohorted[cohorted["trust_cohort"].isin(["Low Trust", "High Trust"])]

    summary = (
        cohorted.groupby("trust_cohort", observed=True)
        .agg(
            sellers=("seller_id", "nunique"),
            avg_trust_score=("trust_score", "mean"),
            avg_return_rate=("cancellation_rate_proxy", "mean"),
            avg_negative_sentiment=("negative_review_rate", "mean"),
            avg_late_delivery_rate=("late_delivery_rate", "mean"),
            avg_review_score=("average_review_score", "mean"),
        )
        .reset_index()
    )

    percent_columns = [
        "avg_return_rate",
        "avg_negative_sentiment",
        "avg_late_delivery_rate",
    ]
    for column in percent_columns:
        summary[column] = (summary[column] * 100).round(1)

    summary["avg_trust_score"] = summary["avg_trust_score"].round(1)
    summary["avg_review_score"] = summary["avg_review_score"].round(2)
    return summary
