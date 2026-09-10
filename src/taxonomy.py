"""Canonical seller risk taxonomy shared by pipeline and dashboard consumers."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config_loader import get_config

INSUFFICIENT_DATA = "Insufficient Data"


def risk_tier_for_score(score: Any) -> str:
    """Return the canonical seller risk tier for a trust score."""
    if pd.isna(score):
        return INSUFFICIENT_DATA

    config = get_config()["risk_tier_bins"]
    bins = config["bins"]
    labels = config["labels"]
    for upper_bound, label in zip(bins[1:], labels):
        if score <= upper_bound:
            return label
    return labels[-1]


def add_canonical_risk_tier(metrics: pd.DataFrame) -> pd.DataFrame:
    """Add the canonical score-based ``risk_tier`` column to seller metrics."""
    prepared = metrics.copy()
    prepared["risk_tier"] = prepared["trust_score"].map(risk_tier_for_score)
    return prepared
