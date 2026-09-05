from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.overview import prepare_seller_metrics
from src.sql_loader import DEFAULT_DB_PATH
from src.trust_score import calculate_trust_score

RISK_SIGNAL_COLUMNS = [
    "cancellation_rate_proxy",
    "late_delivery_rate",
    "negative_review_rate",
    "average_response_time_hours",
    "average_review_score",
    "trust_score",
]

MONTHLY_SIGNAL_COLUMNS = [
    "seller_id",
    "purchase_month",
    "total_orders",
    "trust_score",
    "cancellation_rate_proxy",
    "late_delivery_rate",
    "negative_review_rate",
    "average_review_score",
]


def prepare_signal_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    """Return scored, eligible seller metrics for behaviour-signal visuals."""
    prepared = prepare_seller_metrics(metrics)
    eligible_flag = prepared["eligible_for_risk_score"]
    if not pd.api.types.is_bool_dtype(eligible_flag):
        eligible_flag = eligible_flag.astype("string").str.lower().isin(["true", "1", "yes"])
    eligible = prepared[eligible_flag].copy()
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
    available_columns = [column for column in RISK_SIGNAL_COLUMNS if column in metrics.columns]
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


def load_seller_order_fact(
    seller_ids: list[str] | pd.Series | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Load order-level facts for the selected sellers from SQLite."""
    db_file = Path(db_path)
    if not db_file.is_file():
        raise FileNotFoundError(f"SQLite database not found: {db_file}")

    query = "SELECT * FROM seller_order_fact"
    params: list[str] = []
    if seller_ids is not None:
        seller_values = [seller_id for seller_id in seller_ids if pd.notna(seller_id)]
        if not seller_values:
            return pd.DataFrame()
        placeholders = ", ".join(["?"] * len(seller_values))
        query += f" WHERE seller_id IN ({placeholders})"
        params.extend(seller_values)

    with sqlite3.connect(str(db_file)) as conn:
        return pd.read_sql_query(query, conn, params=params)


def prepare_monthly_seller_metrics(order_fact: pd.DataFrame) -> pd.DataFrame:
    """Roll order facts into seller-month metrics and calculate monthly trust score."""
    if order_fact.empty:
        return pd.DataFrame(columns=MONTHLY_SIGNAL_COLUMNS)

    fact = order_fact.copy()
    fact["purchase_month"] = fact["purchase_month"].fillna(
        pd.to_datetime(
            fact["order_purchase_timestamp"],
            errors="coerce",
        )
        .dt.to_period("M")
        .astype("string")
    )
    fact["review_score"] = pd.to_numeric(fact["review_score"], errors="coerce")
    fact["is_late_delivery"] = pd.to_numeric(fact["is_late_delivery"], errors="coerce").fillna(0)
    fact["response_time_hours"] = pd.to_numeric(fact["response_time_hours"], errors="coerce")

    monthly = fact.groupby(["seller_id", "purchase_month"], as_index=False).agg(
        total_orders=("order_id", "nunique"),
        cancelled_orders=(
            "order_status",
            lambda values: int(values.astype("string").str.lower().eq("canceled").sum()),
        ),
        late_delivery_rate=("is_late_delivery", "mean"),
        average_delivery_delay_days=("delivery_delay_days", "mean"),
        average_review_score=("review_score", "mean"),
        negative_review_rate=(
            "review_score",
            lambda values: float(values.dropna().le(2).mean()) if values.notna().any() else 0.0,
        ),
        average_response_time_hours=("response_time_hours", "mean"),
    )
    monthly["cancellation_rate_proxy"] = monthly["cancelled_orders"] / monthly["total_orders"]
    monthly["eligible_for_risk_score"] = monthly["total_orders"] >= 1
    scored = calculate_trust_score(monthly)
    scored["purchase_month"] = pd.to_datetime(
        scored["purchase_month"],
        errors="coerce",
    )
    return scored.dropna(subset=["purchase_month", "trust_score"])


def build_trust_score_trend(monthly_metrics: pd.DataFrame) -> go.Figure:
    """Build a monthly trust-score trend line for seller performance."""
    trend = (
        monthly_metrics.groupby("purchase_month", as_index=False)
        .agg(
            avg_trust_score=("trust_score", "mean"),
            sellers=("seller_id", "nunique"),
            total_orders=("total_orders", "sum"),
        )
        .sort_values("purchase_month")
    )
    fig = px.line(
        trend,
        x="purchase_month",
        y="avg_trust_score",
        markers=True,
        hover_data={"sellers": True, "total_orders": True, "avg_trust_score": ":.2f"},
        labels={
            "purchase_month": "Purchase Month",
            "avg_trust_score": "Average Trust Score",
            "sellers": "Active Sellers",
            "total_orders": "Orders",
        },
        title="Seller Trust Score Trend Over Time",
    )
    fig.update_layout(height=420, margin={"l": 20, "r": 20, "t": 60, "b": 20})
    return fig


def build_monthly_sentiment_bar(order_fact: pd.DataFrame) -> go.Figure:
    """Build a stacked monthly sentiment distribution chart."""
    if order_fact.empty:
        sentiment = pd.DataFrame(columns=["purchase_month", "sentiment_bucket", "review_count"])
    else:
        fact = order_fact.copy()
        fact["purchase_month"] = pd.to_datetime(
            fact["purchase_month"].fillna(
                pd.to_datetime(
                    fact["order_purchase_timestamp"],
                    errors="coerce",
                )
                .dt.to_period("M")
                .astype("string")
            ),
            errors="coerce",
        )
        sentiment = (
            fact.dropna(subset=["purchase_month", "sentiment_bucket"])
            .groupby(["purchase_month", "sentiment_bucket"], as_index=False)
            .agg(review_count=("order_id", "nunique"))
        )

    fig = px.bar(
        sentiment,
        x="purchase_month",
        y="review_count",
        color="sentiment_bucket",
        barmode="stack",
        category_orders={
            "sentiment_bucket": ["negative", "neutral", "positive"],
        },
        color_discrete_map={
            "negative": "#d62728",
            "neutral": "#ffbf00",
            "positive": "#2ca02c",
        },
        hover_data={"review_count": True, "sentiment_bucket": True},
        labels={
            "purchase_month": "Purchase Month",
            "review_count": "Reviewed Orders",
            "sentiment_bucket": "Sentiment",
        },
        title="Monthly Sentiment Distribution",
    )
    fig.update_layout(height=420, margin={"l": 20, "r": 20, "t": 60, "b": 20})
    return fig


def build_performance_decay_chart(monthly_metrics: pd.DataFrame) -> go.Figure:
    """Show sellers with the largest drop from first to latest monthly trust score."""
    ordered = monthly_metrics.sort_values(["seller_id", "purchase_month"])
    first_last = (
        ordered.groupby("seller_id")
        .agg(
            first_month=("purchase_month", "first"),
            latest_month=("purchase_month", "last"),
            first_trust_score=("trust_score", "first"),
            latest_trust_score=("trust_score", "last"),
            observed_months=("purchase_month", "nunique"),
        )
        .reset_index()
    )
    first_last["trust_score_change"] = first_last["latest_trust_score"] - first_last["first_trust_score"]
    declining = first_last[first_last["observed_months"] >= 2].sort_values("trust_score_change").head(10)

    fig = px.bar(
        declining,
        x="trust_score_change",
        y="seller_id",
        orientation="h",
        color="trust_score_change",
        color_continuous_scale="Reds_r",
        hover_data={
            "first_month": True,
            "latest_month": True,
            "first_trust_score": ":.2f",
            "latest_trust_score": ":.2f",
            "observed_months": True,
        },
        labels={
            "seller_id": "Seller",
            "trust_score_change": "Trust Score Change",
            "first_month": "First Month",
            "latest_month": "Latest Month",
            "first_trust_score": "First Trust Score",
            "latest_trust_score": "Latest Trust Score",
            "observed_months": "Observed Months",
        },
        title="Seller Performance Decay",
    )
    fig.update_layout(height=420, margin={"l": 20, "r": 20, "t": 60, "b": 20})
    return fig
