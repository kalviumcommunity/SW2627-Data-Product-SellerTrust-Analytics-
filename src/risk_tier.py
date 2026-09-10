"""Canonical seller risk tier assignment based on trust score thresholds."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.taxonomy import add_canonical_risk_tier, risk_tier_for_score


def assign_risk_tier(row: pd.Series) -> str:
    """Assign the canonical risk tier from a seller's trust score."""
    return risk_tier_for_score(row.get("trust_score"))


def add_risk_tiers(seller_metrics: pd.DataFrame) -> pd.DataFrame:
    """Add the canonical score-based risk_tier column to seller metrics."""
    scored = seller_metrics.copy()
    if "trust_score" not in scored.columns:
        from src.trust_score import calculate_trust_score

        scored = calculate_trust_score(scored)
    return add_canonical_risk_tier(scored)


def get_tier_distribution(seller_metrics: pd.DataFrame) -> pd.Series:
    """Get count of sellers per risk tier."""
    return seller_metrics["risk_tier"].value_counts()


if __name__ == "__main__":
    # Quick test with pipeline output
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.pipeline import run_pipeline

    outputs = run_pipeline("data/raw", "data/processed")
    metrics = outputs["seller_metrics"]
    metrics = add_risk_tiers(metrics)

    print("Risk Tier Distribution:")
    print(get_tier_distribution(metrics))
    print("\nEligible sellers only:")
    eligible = metrics[metrics["eligible_for_risk_score"]]
    print(get_tier_distribution(eligible))
