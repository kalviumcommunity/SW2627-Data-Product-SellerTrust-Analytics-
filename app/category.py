from __future__ import annotations

from io import StringIO

import pandas as pd

from src.config_loader import get_config

MIN_CATEGORY_ORDERS = 10


def _category_name(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().replace({"": pd.NA}).fillna("unknown")


def build_category_analysis(seller_metrics: pd.DataFrame, order_fact: pd.DataFrame) -> pd.DataFrame:
    """Build category rollups using one seller contribution per category."""
    if seller_metrics.empty or order_fact.empty:
        return pd.DataFrame()
    fact = order_fact.copy()
    fact["product_category_name"] = _category_name(fact["product_category_name"])
    fact["is_late_delivery"] = pd.to_numeric(fact["is_late_delivery"], errors="coerce")
    fact["review_score"] = pd.to_numeric(fact["review_score"], errors="coerce")
    fact["is_cancelled"] = fact["order_status"].astype("string").str.lower().eq("canceled")
    seller_columns = [
        "seller_id",
        "trust_score",
        "risk_tier",
        "late_delivery_rate",
        "cancellation_rate_proxy",
        "average_review_score",
        "negative_review_rate",
    ]
    available = [column for column in seller_columns if column in seller_metrics.columns]
    seller_category = (
        fact[["product_category_name", "seller_id"]]
        .drop_duplicates()
        .merge(seller_metrics[available], on="seller_id", how="inner")
    )
    order_rollup = fact.groupby("product_category_name", as_index=False).agg(
        total_orders=("order_id", "nunique"),
        late_delivery_rate=("is_late_delivery", "mean"),
        average_review_score=("review_score", "mean"),
        negative_review_rate=("review_score", lambda values: values.dropna().le(2).mean()),
        cancellation_rate_proxy=("is_cancelled", "mean"),
    )
    seller_rollup = seller_category.groupby("product_category_name", as_index=False).agg(
        unique_sellers=("seller_id", "nunique"),
        avg_trust_score=("trust_score", "mean"),
    )
    result = order_rollup.merge(seller_rollup, on="product_category_name", how="left")
    if "risk_tier" in seller_category:
        risk_counts = pd.crosstab(seller_category["product_category_name"], seller_category["risk_tier"])
        risk_counts.columns = [
            f"risk_{str(column).lower().replace('-', '_').replace(' ', '_')}_count" for column in risk_counts.columns
        ]
        result = result.merge(risk_counts.reset_index(), on="product_category_name", how="left")
    thresholds = get_config().get("action_tiers", {})
    coach = thresholds.get("coach", {})
    drivers = []
    for _, row in result.iterrows():
        candidates = []
        late_threshold = coach.get("late_delivery_rate", 0.05)
        negative_threshold = coach.get("negative_review_rate", 0.15)
        cancellation_threshold = coach.get("cancellation_rate_proxy", 0.0125)
        review_threshold = coach.get("average_review_score", 3.8)
        if pd.notna(row["late_delivery_rate"]) and row["late_delivery_rate"] > late_threshold:
            candidates.append((row["late_delivery_rate"] - late_threshold, "Late delivery"))
        if pd.notna(row["negative_review_rate"]) and row["negative_review_rate"] > negative_threshold:
            candidates.append((row["negative_review_rate"] - negative_threshold, "Negative reviews"))
        if pd.notna(row["cancellation_rate_proxy"]) and row["cancellation_rate_proxy"] > cancellation_threshold:
            candidates.append((row["cancellation_rate_proxy"] - cancellation_threshold, "Cancellations"))
        if pd.notna(row["average_review_score"]) and row["average_review_score"] < review_threshold:
            candidates.append((review_threshold - row["average_review_score"], "Review quality"))
        drivers.append(", ".join(label for _, label in sorted(candidates, reverse=True)) or "No configured drivers")
    result["top_trust_eroding_behaviours"] = drivers
    result["sample_warning"] = result["total_orders"] < MIN_CATEGORY_ORDERS
    result = result.rename(columns={"product_category_name": "category"})
    return result.sort_values(
        ["sample_warning", "avg_trust_score"], ascending=[True, True], na_position="last"
    ).reset_index(drop=True)


def category_analysis_csv(analysis: pd.DataFrame) -> bytes:
    """Serialize the category rollup for download."""
    buffer = StringIO()
    analysis.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")
