"""Assemble a single seller's health report (issue #46).

Gathers everything the pipeline knows about one seller — metrics, trust score,
risk tier, review trend, anomalies and recommended actions — into a plain dict,
then renders it through a Jinja2 template. Keeping the gathering separate from
the rendering means the report content is testable without parsing HTML.

Nothing here recomputes a metric. Every number comes from a pipeline output, so
a report can never disagree with the dashboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
TEMPLATE_NAME = "seller_report.html.j2"

TREND_LABELS = {
    "declining": ("Declining", "Review scores are falling and the trend is statistically significant."),
    "improving": ("Improving", "Review scores are rising and the trend is statistically significant."),
    "stable": ("Stable", "No statistically significant movement in review scores."),
    "insufficient_data": ("Insufficient data", "Too few reviews over time to fit a trend."),
}

METRIC_LABELS = [
    ("trust_score", "Trust score", "score"),
    ("total_orders", "Total orders", "int"),
    ("cancelled_orders", "Cancelled orders", "int"),
    ("late_delivery_rate", "Late delivery rate", "pct"),
    ("average_delivery_delay_days", "Average delivery delay", "days"),
    ("average_review_score", "Average review score", "review"),
    ("negative_review_rate", "Negative review rate", "pct"),
    ("cancellation_rate_proxy", "Cancellation rate", "pct"),
    ("average_response_time_hours", "Average review response time", "hours"),
]


class SellerNotFoundError(ValueError):
    """Raised when the requested seller id is not in the processed metrics."""


def format_value(value: Any, kind: str) -> str:
    """Render a metric for display, distinguishing 'zero' from 'not known'."""
    if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
        return "n/a"
    if kind == "pct":
        return f"{float(value):.1%}"
    if kind == "int":
        return f"{int(value):,}"
    if kind == "score":
        return f"{float(value):.1f} / 100"
    if kind == "review":
        return f"{float(value):.2f} / 5"
    if kind == "days":
        days = float(value)
        return f"{days:+.1f} days" + (" (early)" if days < 0 else "" if days == 0 else " (late)")
    if kind == "hours":
        return f"{float(value):.1f} h"
    return str(value)


def _monthly_history(fact: pd.DataFrame, seller_id: str) -> list[dict[str, Any]]:
    """Month-by-month review score and late delivery rate for the chart."""
    rows = fact[fact["seller_id"] == seller_id].copy()
    if rows.empty:
        return []
    rows["month"] = pd.to_datetime(rows["order_purchase_timestamp"], errors="coerce").dt.to_period("M")
    rows = rows.dropna(subset=["month"])
    monthly = rows.groupby("month").agg(
        orders=("order_id", "nunique"),
        average_review_score=("review_score", "mean"),
        late_delivery_rate=("is_late_delivery", "mean"),
    )
    return [
        {
            "month": str(month),
            "orders": int(row["orders"]),
            "average_review_score": (
                None if pd.isna(row["average_review_score"]) else float(row["average_review_score"])
            ),
            "late_delivery_rate": None if pd.isna(row["late_delivery_rate"]) else float(row["late_delivery_rate"]),
        }
        for month, row in monthly.iterrows()
    ]


def _active_anomalies(anomalies: pd.DataFrame, seller_id: str) -> list[str]:
    """Metrics flagged anomalous for this seller, named once each with the detector that fired.

    The anomalies frame carries three columns per metric — `_iqr_outlier`, `_zscore_anomaly`
    and a `_anomaly` summary of the two. Listing every truthy column would name the same
    metric up to three times, so this reads the summary column and reports which detector
    was responsible.
    """
    rows = anomalies[anomalies["seller_id"] == seller_id]
    if rows.empty:
        return []
    row = rows.iloc[0]

    flagged = []
    for column in anomalies.columns:
        if not column.endswith("_anomaly") or column.endswith("_zscore_anomaly"):
            continue
        metric = column.removesuffix("_anomaly")
        # Only per-metric summary columns qualify. `any_anomaly` and `is_anomaly` also end
        # in "_anomaly" but describe the seller, not a metric, and would otherwise be
        # listed as an anomaly named "any" or "is".
        if f"{metric}_iqr_outlier" not in anomalies.columns:
            continue
        if not bool(row[column]):
            continue
        methods = []
        if bool(row.get(f"{metric}_iqr_outlier", False)):
            methods.append("IQR")
        if bool(row.get(f"{metric}_zscore_anomaly", False)):
            methods.append("z-score")
        label = metric.replace("_", " ")
        flagged.append(f"{label} ({', '.join(methods)})" if methods else label)
    return sorted(flagged)


def collect_seller_report(
    seller_id: str,
    metrics: pd.DataFrame,
    fact: pd.DataFrame,
    trends: pd.DataFrame | None = None,
    anomalies: pd.DataFrame | None = None,
    actions: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Gather every fact the report needs for one seller.

    Raises:
        SellerNotFoundError: If the seller id is absent from `metrics`.
    """
    matched = metrics[metrics["seller_id"] == seller_id]
    if matched.empty:
        raise SellerNotFoundError(f"Seller {seller_id!r} is not in the processed metrics.")
    row = matched.iloc[0]

    trend: dict[str, Any] = {
        "flag": "insufficient_data",
        "label": TREND_LABELS["insufficient_data"][0],
        "description": TREND_LABELS["insufficient_data"][1],
        "slope": None,
        "p_value": None,
    }
    if trends is not None:
        trend_rows = trends[trends["seller_id"] == seller_id]
        if not trend_rows.empty:
            trend_row = trend_rows.iloc[0]
            flag = str(trend_row.get("trend_flag", "insufficient_data"))
            label, description = TREND_LABELS.get(flag, (flag, ""))
            trend = {
                "flag": flag,
                "label": label,
                "description": description,
                "slope": None if pd.isna(trend_row.get("slope")) else float(trend_row["slope"]),
                "p_value": None if pd.isna(trend_row.get("p_value")) else float(trend_row["p_value"]),
            }

    anomaly_count = 0
    anomaly_metrics: list[str] = []
    if anomalies is not None:
        anomaly_rows = anomalies[anomalies["seller_id"] == seller_id]
        if not anomaly_rows.empty and "anomaly_count" in anomaly_rows.columns:
            anomaly_count = int(anomaly_rows.iloc[0]["anomaly_count"])
        anomaly_metrics = _active_anomalies(anomalies, seller_id)

    recommended_action = "Not assessed"
    evidence: list[str] = []
    if actions is not None:
        action_rows = actions[actions["seller_id"] == seller_id]
        if not action_rows.empty:
            action_row = action_rows.iloc[0]
            recommended_action = str(action_row.get("recommended_action", recommended_action))
            raw_evidence = action_row.get("evidence", [])
            evidence = list(raw_evidence) if isinstance(raw_evidence, (list, tuple)) else []

    eligible = bool(row.get("eligible_for_risk_score", False))

    return {
        "seller_id": seller_id,
        "eligible": eligible,
        "eligibility_note": (
            None
            if eligible
            else f"This seller has {int(row['total_orders'])} orders, below the 5-order floor for trust "
            "scoring. The metrics below are real but rest on a very small sample; read the risk "
            "tier as a triage hint rather than a measurement."
        ),
        "risk_tier": row.get("risk_tier", "n/a"),
        "trust_score": None if pd.isna(row.get("trust_score")) else float(row["trust_score"]),
        "metrics": [
            {"label": label, "value": format_value(row.get(column), kind), "key": column}
            for column, label, kind in METRIC_LABELS
        ],
        "trend": trend,
        "anomaly_count": anomaly_count,
        "anomaly_metrics": anomaly_metrics,
        "recommended_action": recommended_action,
        "evidence": evidence,
        "history": _monthly_history(fact, seller_id),
    }


def build_history_chart(history: list[dict[str, Any]], seller_id: str) -> str:
    """Return an embeddable Plotly chart of the seller's monthly performance.

    Plotly.js is pulled from a CDN rather than inlined, so the report stays a
    small file. Returns an empty string when there is nothing to plot.
    """
    if len(history) < 2:
        return ""
    import plotly.graph_objects as go

    months = [point["month"] for point in history]
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=months,
            y=[point["average_review_score"] for point in history],
            name="Average review score",
            mode="lines+markers",
            yaxis="y",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=months,
            y=[None if point["late_delivery_rate"] is None else point["late_delivery_rate"] * 100 for point in history],
            name="Late delivery rate (%)",
            mode="lines+markers",
            yaxis="y2",
        )
    )
    figure.update_layout(
        title=f"Monthly performance — {seller_id[:12]}…",
        xaxis={"title": "Month"},
        yaxis={"title": "Average review score", "range": [0, 5.2]},
        yaxis2={"title": "Late delivery rate (%)", "overlaying": "y", "side": "right", "rangemode": "tozero"},
        legend={"orientation": "h", "y": -0.25},
        margin={"l": 60, "r": 60, "t": 50, "b": 60},
        height=380,
    )
    return figure.to_html(full_html=False, include_plotlyjs="cdn")


def render_report(report: dict[str, Any], chart_html: str = "", template_dir: Path | None = None) -> str:
    """Render the gathered report through the Jinja2 template."""
    environment = Environment(
        loader=FileSystemLoader(template_dir or TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template(TEMPLATE_NAME)
    return template.render(report=report, chart_html=chart_html)
