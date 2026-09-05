"""Risk tier assignment based on configurable action thresholds."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


CONFIG_PATH = Path(__file__).parent / "config" / "thresholds.yaml"


def load_thresholds() -> dict:
    """Load thresholds from YAML config."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


THRESHOLDS = load_thresholds()


def assign_risk_tier(row: pd.Series) -> str:
    """Assign risk tier based on action thresholds.

    Tiers:
    - ESCALATE: At/above marketplace suspension thresholds
    - COACH: Between internal target (50% of threshold) and suspension threshold
    - MONITOR: Below internal targets (healthy performance)
    """
    esc = THRESHOLDS["action_tiers"]["escalate"]
    coach = THRESHOLDS["action_tiers"]["coach"]

    # Handle NA values - treat as not meeting threshold
    def check_ge(val, threshold):
        if pd.isna(val):
            return False
        return val >= threshold

    def check_lt(val, threshold):
        if pd.isna(val):
            return False
        return val < threshold

    escalate = (
        check_ge(row["cancellation_rate_proxy"], esc["cancellation_rate_proxy"])
        or check_ge(row["negative_review_rate"], esc["negative_review_rate"])
        or check_ge(row["late_delivery_rate"], esc["late_delivery_rate"])
        or check_lt(row["average_review_score"], esc["average_review_score"])
    )

    coach_tier = (
        check_ge(row["cancellation_rate_proxy"], coach["cancellation_rate_proxy"])
        or check_ge(row["negative_review_rate"], coach["negative_review_rate"])
        or check_ge(row["late_delivery_rate"], coach["late_delivery_rate"])
        or check_lt(row["average_review_score"], coach["average_review_score"])
    )

    if escalate:
        return "ESCALATE"
    elif coach_tier:
        return "COACH"
    else:
        return "MONITOR"


def add_risk_tiers(seller_metrics: pd.DataFrame) -> pd.DataFrame:
    """Add risk_tier column to seller metrics DataFrame."""
    scored = seller_metrics.copy()
    scored["risk_tier"] = scored.apply(assign_risk_tier, axis=1)
    return scored


def get_tier_distribution(seller_metrics: pd.DataFrame) -> pd.Series:
    """Get count of sellers per risk tier."""
    return seller_metrics["risk_tier"].value_counts()


if __name__ == "__main__":
    # Quick test with pipeline output
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from pipeline import run_pipeline

    outputs = run_pipeline("data/raw", "data/processed")
    metrics = outputs["seller_metrics"]
    metrics = add_risk_tiers(metrics)

    print("Risk Tier Distribution:")
    print(get_tier_distribution(metrics))
    print("\nEligible sellers only:")
    eligible = metrics[metrics["eligible_for_risk_score"]]
    print(get_tier_distribution(eligible))
