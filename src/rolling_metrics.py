"""Rolling metrics: computes 30-day rolling windows for seller time-series analysis."""

from __future__ import annotations

import pandas as pd


def compute_rolling_metrics(
    order_fact: pd.DataFrame,
    window_days: int = 30,
) -> pd.DataFrame:
    """Compute rolling metrics per seller over a configurable time window.

    For each seller-month, calculates rolling averages of:
        - review_score
        - cancellation_rate (orders cancelled / total orders)
        - late_delivery_rate

    Handles sellers with sparse order history by using expanding windows
    when fewer than window_days of data are available.

    Returns a DataFrame with columns:
        - seller_id
        - purchase_month
        - rolling_avg_review_score
        - rolling_cancellation_rate
        - rolling_late_delivery_rate
        - window_size (number of days in the window used)
    """
    if order_fact.empty:
        return pd.DataFrame(
            columns=[
                "seller_id",
                "purchase_month",
                "rolling_avg_review_score",
                "rolling_cancellation_rate",
                "rolling_late_delivery_rate",
                "window_size",
            ]
        )

    fact = order_fact.copy()
    fact["purchase_month"] = pd.to_datetime(
        fact["purchase_month"].fillna(
            pd.to_datetime(fact["order_purchase_timestamp"], errors="coerce").dt.to_period("M").astype("string")
        ),
        errors="coerce",
    )
    fact["review_score"] = pd.to_numeric(fact["review_score"], errors="coerce")
    fact["is_late_delivery"] = pd.to_numeric(fact["is_late_delivery"], errors="coerce").fillna(0)
    fact["is_cancelled"] = fact["order_status"].astype(str).str.lower().eq("canceled").astype(int)

    monthly = fact.groupby(["seller_id", "purchase_month"], as_index=False).agg(
        total_orders=("order_id", "nunique"),
        cancelled_orders=("is_cancelled", "sum"),
        late_deliveries=("is_late_delivery", "sum"),
        avg_review_score=("review_score", "mean"),
    )
    monthly["cancellation_rate"] = monthly["cancelled_orders"] / monthly["total_orders"]
    monthly["late_delivery_rate"] = monthly["late_deliveries"] / monthly["total_orders"]

    monthly = monthly.sort_values(["seller_id", "purchase_month"])

    result_parts = []
    for seller_id, group in monthly.groupby("seller_id"):
        group = group.sort_values("purchase_month").copy()
        n = len(group)

        if n == 0:
            continue

        window = min(window_days, n)

        group["rolling_avg_review_score"] = (
            group["avg_review_score"].rolling(window=window, min_periods=1).mean().round(2)
        )
        group["rolling_cancellation_rate"] = (
            group["cancellation_rate"].rolling(window=window, min_periods=1).mean().round(4)
        )
        group["rolling_late_delivery_rate"] = (
            group["late_delivery_rate"].rolling(window=window, min_periods=1).mean().round(4)
        )
        group["window_size"] = window

        result_parts.append(
            group[
                [
                    "seller_id",
                    "purchase_month",
                    "rolling_avg_review_score",
                    "rolling_cancellation_rate",
                    "rolling_late_delivery_rate",
                    "window_size",
                ]
            ]
        )

    if not result_parts:
        return pd.DataFrame(
            columns=[
                "seller_id",
                "purchase_month",
                "rolling_avg_review_score",
                "rolling_cancellation_rate",
                "rolling_late_delivery_rate",
                "window_size",
            ]
        )

    return pd.concat(result_parts, ignore_index=True)
