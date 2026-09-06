"""Reusable Day 1–9 ingestion, cleaning, merge, and seller-metric pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_quality import add_delivery_features
from src.trust_score import calculate_trust_score
from src.risk_tier import add_risk_tiers


REQUIRED_FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
}


def load_olist_sources(raw_directory: str | Path) -> dict[str, pd.DataFrame]:
    """Load the five v1 Olist files and report every missing file at once."""
    raw_path = Path(raw_directory)
    missing = [filename for filename in REQUIRED_FILES.values() if not (raw_path / filename).is_file()]
    if missing:
        raise FileNotFoundError("Missing required raw files: " + ", ".join(missing))
    return {
        name: pd.read_csv(raw_path / filename)
        for name, filename in REQUIRED_FILES.items()
    }


def profile_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the Day 6 profiling metrics used to make cleaning decisions."""
    return pd.DataFrame(
        {
            "column": frame.columns,
            "dtype": [str(frame[column].dtype) for column in frame.columns],
            "null_count": [int(frame[column].isna().sum()) for column in frame.columns],
            "null_pct": [round(float(frame[column].isna().mean() * 100), 2) for column in frame.columns],
            "distinct_count": [int(frame[column].nunique(dropna=True)) for column in frame.columns],
        }
    )


def normalise_text(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Trim and case-normalise categorical text without changing null values."""
    cleaned = frame.copy()
    for column in columns:
        if column in cleaned:
            cleaned[column] = cleaned[column].astype("string").str.strip().str.lower()
    return cleaned


def remove_exact_duplicates(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove only byte-for-byte duplicate records; retain legitimate repeat events."""
    return frame.drop_duplicates().copy()


def clean_sources(sources: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Apply the Day 6–8 cleaning decisions before tables are merged."""
    cleaned = {name: remove_exact_duplicates(frame) for name, frame in sources.items()}
    cleaned["orders"] = add_delivery_features(
        normalise_text(cleaned["orders"], ["order_status"])
    )
    cleaned["sellers"] = normalise_text(cleaned["sellers"], ["seller_city", "seller_state"])
    cleaned["products"] = normalise_text(cleaned["products"], ["product_category_name"])
    cleaned["reviews"] = normalise_text(cleaned["reviews"], [])
    cleaned["reviews"]["review_score"] = pd.to_numeric(
        cleaned["reviews"]["review_score"], errors="coerce"
    ).astype("Int64")
    for column in ("review_creation_date", "review_answer_timestamp"):
        if column in cleaned["reviews"]:
            cleaned["reviews"][column] = pd.to_datetime(cleaned["reviews"][column], errors="coerce")
    return cleaned


def build_seller_order_fact(cleaned: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create one seller-order record, preventing item-level double counting."""
    items = cleaned["items"].merge(
        cleaned["products"][["product_id", "product_category_name"]],
        on="product_id",
        how="left",
        validate="m:1",
    )
    seller_orders = (
        items.groupby(["order_id", "seller_id"], as_index=False)
        .agg(
            item_count=("product_id", "size"),
            item_value=("price", "sum"),
            freight_value=("freight_value", "sum"),
            product_category_name=("product_category_name", "first"),
        )
        .merge(cleaned["orders"], on="order_id", how="left", validate="m:1")
        .merge(cleaned["sellers"], on="seller_id", how="left", validate="m:1")
    )
    reviews = cleaned["reviews"].copy()
    for column in ("review_creation_date", "review_answer_timestamp"):
        reviews[column] = pd.to_datetime(reviews[column], errors="coerce")
    reviews["response_time_hours"] = (
        reviews["review_answer_timestamp"] - reviews["review_creation_date"]
    ).dt.total_seconds() / 3600
    review_summary = (
        reviews.groupby("order_id", as_index=False)
        .agg(
            review_score=("review_score", "mean"),
            review_count=("review_id", "nunique"),
            response_time_hours=("response_time_hours", "mean"),
        )
    )
    fact = seller_orders.merge(review_summary, on="order_id", how="left", validate="m:1")
    fact["sentiment_bucket"] = pd.cut(
        fact["review_score"], bins=[0, 2, 3, 5], labels=["negative", "neutral", "positive"]
    ).astype("string")
    return fact


def build_seller_metrics(seller_orders: pd.DataFrame) -> pd.DataFrame:
    """Produce seller-level v1 metrics using the PRD's locked proxy definitions."""
    # Late delivery rate: use delivered orders with valid dates as denominator (industry standard)
    # is_late_delivery is True only for delivered orders with valid dates that are late
    # For cancelled/pending orders, is_late_delivery is NaN (excluded from mean)
    # But we need explicit denominator: delivered orders with valid delivery dates
    delivered_with_dates = seller_orders.dropna(subset=["order_delivered_customer_date", "order_estimated_delivery_date"])
    delivered_with_dates = delivered_with_dates[delivered_with_dates["order_status"] == "delivered"]

    late_rates = delivered_with_dates.groupby("seller_id").apply(
        lambda g: (g["is_late_delivery"] == True).sum() / len(g) if len(g) > 0 else 0.0
    ).rename("late_delivery_rate")

    avg_delays = delivered_with_dates.groupby("seller_id")["delivery_delay_days"].mean().rename("average_delivery_delay_days")

    metrics = seller_orders.groupby("seller_id", as_index=False).agg(
        total_orders=("order_id", "nunique"),
        cancelled_orders=("order_status", lambda values: int((values == "canceled").sum())),
        average_review_score=("review_score", "mean"),
        negative_review_rate=("review_score", lambda s: float(s.dropna().le(2).mean()) if s.notna().any() else 0.0),
        average_response_time_hours=("response_time_hours", "mean"),
    )

    # Merge corrected delivery metrics
    metrics = metrics.merge(late_rates.reset_index(), on="seller_id", how="left")
    metrics = metrics.merge(avg_delays.reset_index(), on="seller_id", how="left")

    # Fill NaN for sellers with no delivered orders with valid dates
    metrics["late_delivery_rate"] = metrics["late_delivery_rate"].fillna(0.0)
    metrics["average_delivery_delay_days"] = metrics["average_delivery_delay_days"].fillna(0.0)

    metrics["cancellation_rate_proxy"] = metrics["cancelled_orders"] / metrics["total_orders"]
    metrics["eligible_for_risk_score"] = metrics["total_orders"] >= 5
    return metrics


def run_pipeline(raw_directory: str | Path, output_directory: str | Path) -> dict[str, pd.DataFrame]:
    """Run the repeatable Day 1–9 workflow and write dashboard-ready CSV outputs."""
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    sources = load_olist_sources(raw_directory)
    cleaned = clean_sources(sources)
    fact = build_seller_order_fact(cleaned)
    metrics = build_seller_metrics(fact)
    metrics = calculate_trust_score(metrics)
    metrics = add_risk_tiers(metrics)
    for name, frame in {"seller_order_fact": fact, "seller_metrics": metrics}.items():
        frame.to_csv(output_path / f"{name}.csv", index=False)
    return {"seller_order_fact": fact, "seller_metrics": metrics}
