"""Trend detection for seller review scores over time using linear regression."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def compute_seller_review_trends(
    seller_order_fact: pd.DataFrame,
    time_column: str = "order_purchase_timestamp",
    score_column: str = "review_score",
    seller_column: str = "seller_id",
    min_orders: int = 5,
    p_value_threshold: float = 0.05,
) -> pd.DataFrame:
    """
    Compute linear regression trend of review scores over time for each seller.

    Args:
        seller_order_fact: DataFrame with seller orders, review scores, and timestamps
        time_column: Column name for the time variable (default: order_purchase_timestamp)
        score_column: Column name for the review score (default: review_score)
        seller_column: Column name for seller identifier (default: seller_id)
        min_orders: Minimum number of orders with reviews required for trend analysis
        p_value_threshold: P-value threshold for statistical significance

    Returns:
        DataFrame with trend analysis per seller including slope, p-value, and trend_flag
    """
    # Ensure time column is datetime
    df = seller_order_fact.copy()
    df[time_column] = pd.to_datetime(df[time_column], errors="coerce")
    df[score_column] = pd.to_numeric(df[score_column], errors="coerce")

    # Drop rows with missing time or score
    df = df.dropna(subset=[time_column, score_column, seller_column])

    # Convert time to numeric (days since epoch) for regression
    df["time_numeric"] = (df[time_column] - pd.Timestamp("1970-01-01")).dt.total_seconds() / 86400

    results = []

    for seller_id, group in df.groupby(seller_column):
        # Filter to only orders with valid review scores
        valid_reviews = group.dropna(subset=[score_column])

        if len(valid_reviews) < min_orders:
            results.append(
                {
                    seller_column: seller_id,
                    "n_reviews": len(valid_reviews),
                    "slope": np.nan,
                    "intercept": np.nan,
                    "r_value": np.nan,
                    "p_value": np.nan,
                    "std_err": np.nan,
                    "trend_flag": "insufficient_data",
                }
            )
            continue

        # Perform linear regression: review_score ~ time
        x = valid_reviews["time_numeric"].values
        y = valid_reviews[score_column].values

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # Determine trend flag
        if p_value < p_value_threshold and slope < 0:
            trend_flag = "declining"
        elif p_value < p_value_threshold and slope > 0:
            trend_flag = "improving"
        else:
            trend_flag = "stable"

        results.append(
            {
                seller_column: seller_id,
                "n_reviews": len(valid_reviews),
                "slope": round(slope, 6),
                "intercept": round(intercept, 4),
                "r_value": round(r_value, 4),
                "p_value": round(p_value, 6),
                "std_err": round(std_err, 6),
                "trend_flag": trend_flag,
            }
        )

    return pd.DataFrame(results)


def run_trend_detection(
    input_path: str,
    output_path: str,
    time_column: str = "order_purchase_timestamp",
    score_column: str = "review_score",
    seller_column: str = "seller_id",
    min_orders: int = 5,
    p_value_threshold: float = 0.05,
) -> pd.DataFrame:
    """
    Run trend detection on seller order fact data and save results.

    Args:
        input_path: Path to seller_order_fact.csv
        output_path: Path to output seller_trends.csv
        time_column: Column name for time variable
        score_column: Column name for review score
        seller_column: Column name for seller ID
        min_orders: Minimum orders for trend analysis
        p_value_threshold: P-value threshold for significance

    Returns:
        DataFrame with trend results
    """
    seller_order_fact = pd.read_csv(input_path)
    trends = compute_seller_review_trends(
        seller_order_fact,
        time_column=time_column,
        score_column=score_column,
        seller_column=seller_column,
        min_orders=min_orders,
        p_value_threshold=p_value_threshold,
    )
    trends.to_csv(output_path, index=False)
    return trends
