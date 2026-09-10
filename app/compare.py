from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.theme import RISK_TIER_COLORS, apply_chart_polish

COMPARE_METRICS = [
    ("trust_score", "Trust Score", "score"),
    ("total_orders", "Total Orders", "count"),
    ("cancellation_rate_proxy", "Return Rate Proxy", "percent"),
    ("negative_review_rate", "Negative Sentiment Rate", "percent"),
    ("late_delivery_rate", "Late Delivery Rate", "percent"),
    ("average_review_score", "Avg Review Score", "score"),
    ("average_response_time_hours", "Avg Response Time Hours", "hours"),
]


def get_seller_options(metrics: pd.DataFrame, limit: int = 250) -> list[str]:
    """Return seller IDs ordered by risk priority for the compare picker."""
    if metrics.empty or "seller_id" not in metrics.columns:
        return []

    ordered = metrics.copy()
    ordered["trust_score"] = pd.to_numeric(ordered.get("trust_score"), errors="coerce")
    ordered = ordered.sort_values(["trust_score", "seller_id"], na_position="last")
    return ordered["seller_id"].dropna().astype(str).drop_duplicates().head(limit).tolist()


def prepare_compare_metrics(metrics: pd.DataFrame, selected_sellers: list[str]) -> pd.DataFrame:
    """Filter seller metrics to the selected sellers and keep compare columns."""
    if not selected_sellers or metrics.empty:
        return pd.DataFrame()

    available_columns = [
        column
        for column in ["seller_id", "risk_tier", *[metric[0] for metric in COMPARE_METRICS]]
        if column in metrics.columns
    ]
    selected = metrics[metrics["seller_id"].astype(str).isin(selected_sellers)][available_columns].copy()
    return selected.sort_values("seller_id").reset_index(drop=True)


def format_compare_value(value: object, value_type: str) -> str:
    """Format a seller comparison metric for dashboard display."""
    if pd.isna(value):
        return "N/A"
    if value_type == "percent":
        return f"{float(value) * 100:.1f}%"
    if value_type == "count":
        return f"{int(value):,}"
    if value_type == "hours":
        return f"{float(value):.1f}h"
    return f"{float(value):.1f}"


def build_side_by_side_table(compare_metrics: pd.DataFrame) -> pd.DataFrame:
    """Build a side-by-side seller metric comparison table."""
    if compare_metrics.empty:
        return pd.DataFrame()

    rows: list[dict[str, str]] = []
    for column, label, value_type in COMPARE_METRICS:
        if column not in compare_metrics.columns:
            continue
        row = {"Metric": label}
        for _, seller in compare_metrics.iterrows():
            row[str(seller["seller_id"])] = format_compare_value(seller[column], value_type)
        rows.append(row)

    return pd.DataFrame(rows)


def build_difference_highlights(compare_metrics: pd.DataFrame) -> pd.DataFrame:
    """Highlight biggest differences across selected seller risk metrics."""
    if compare_metrics.empty:
        return pd.DataFrame()

    rows: list[dict[str, str | float]] = []
    for column, label, value_type in COMPARE_METRICS:
        if column not in compare_metrics.columns:
            continue
        values = pd.to_numeric(compare_metrics[column], errors="coerce")
        if values.dropna().empty:
            continue
        min_idx = values.idxmin()
        max_idx = values.idxmax()
        rows.append(
            {
                "Metric": label,
                "Lowest Seller": str(compare_metrics.loc[min_idx, "seller_id"]),
                "Lowest Value": format_compare_value(values.loc[min_idx], value_type),
                "Highest Seller": str(compare_metrics.loc[max_idx, "seller_id"]),
                "Highest Value": format_compare_value(values.loc[max_idx], value_type),
                "Gap": format_compare_value(values.loc[max_idx] - values.loc[min_idx], value_type),
            }
        )

    return pd.DataFrame(rows)


def build_risk_profile_chart(compare_metrics: pd.DataFrame) -> go.Figure:
    """Build grouped bars for selected seller risk profiles."""
    metric_columns = [
        "cancellation_rate_proxy",
        "negative_review_rate",
        "late_delivery_rate",
    ]
    available = [column for column in metric_columns if column in compare_metrics.columns]
    if compare_metrics.empty or not available:
        chart_data = pd.DataFrame(columns=["seller_id", "Metric", "Value"])
    else:
        chart_data = compare_metrics.melt(
            id_vars=["seller_id"],
            value_vars=available,
            var_name="Metric",
            value_name="Value",
        )
        chart_data["Metric"] = chart_data["Metric"].map(
            {
                "cancellation_rate_proxy": "Return Rate",
                "negative_review_rate": "Negative Sentiment",
                "late_delivery_rate": "Late Delivery",
            }
        )

    fig = px.bar(
        chart_data,
        x="Metric",
        y="Value",
        color="seller_id",
        barmode="group",
        text_auto=".1%",
        labels={"seller_id": "Seller", "Value": "Rate"},
        title="Risk Profile Comparison",
    )
    fig.update_yaxes(tickformat=".0%")
    return apply_chart_polish(fig, height=380)


def build_trust_overlay_chart(monthly_metrics: pd.DataFrame) -> go.Figure:
    """Build an overlay line chart comparing selected sellers over time."""
    if monthly_metrics.empty:
        chart_data = pd.DataFrame(columns=["purchase_month", "trust_score", "seller_id", "risk_tier"])
    else:
        chart_data = monthly_metrics.sort_values(["seller_id", "purchase_month"])

    fig = px.line(
        chart_data,
        x="purchase_month",
        y="trust_score",
        color="seller_id",
        markers=True,
        hover_data=["total_orders", "average_review_score", "negative_review_rate"],
        labels={
            "purchase_month": "Purchase Month",
            "trust_score": "Trust Score",
            "seller_id": "Seller",
            "total_orders": "Orders",
            "average_review_score": "Avg Review Score",
            "negative_review_rate": "Negative Sentiment Rate",
        },
        title="Selected Sellers Trust Score Overlay",
    )
    return apply_chart_polish(fig, height=420)


def build_risk_badge_summary(compare_metrics: pd.DataFrame) -> pd.DataFrame:
    """Return compact seller risk profiles for compare mode cards."""
    if compare_metrics.empty:
        return pd.DataFrame()

    summary = compare_metrics[["seller_id", "risk_tier", "trust_score", "total_orders"]].copy()
    summary["risk_color"] = summary["risk_tier"].map(RISK_TIER_COLORS).fillna("#8c8c8c")
    return summary

