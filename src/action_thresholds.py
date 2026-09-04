"""Configurable action thresholds for seller risk tier assignment.

Based on industry benchmarks from Amazon, eBay, Shopify, McKinsey, and Trustpilot.
All thresholds can be overridden via config file or environment variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path


@dataclass
class EscalateThresholds:
    """Thresholds for ESCALATE tier (immediate action required)."""
    return_rate: float = 0.25
    negative_review_rate: float = 0.20
    late_delivery_rate: float = 0.15
    cancellation_rate: float = 0.10
    trust_score_max: float = 30.0
    anomaly_count_min: int = 3


@dataclass
class CoachThresholds:
    """Thresholds for COACH tier (proactive coaching required)."""
    return_rate_min: float = 0.15
    return_rate_max: float = 0.25
    negative_review_rate_min: float = 0.10
    negative_review_rate_max: float = 0.20
    late_delivery_rate_min: float = 0.08
    late_delivery_rate_max: float = 0.15
    cancellation_rate_min: float = 0.05
    cancellation_rate_max: float = 0.10
    trust_score_min: float = 30.0
    trust_score_max: float = 50.0
    anomaly_count_min: int = 1
    anomaly_count_max: int = 2
    declining_trend: bool = True


@dataclass
class MonitorThresholds:
    """Thresholds for MONITOR tier (ongoing monitoring)."""
    return_rate_min: float = 0.08
    return_rate_max: float = 0.15
    negative_review_rate_min: float = 0.05
    negative_review_rate_max: float = 0.10
    late_delivery_rate_min: float = 0.04
    late_delivery_rate_max: float = 0.08
    cancellation_rate_min: float = 0.025
    cancellation_rate_max: float = 0.05
    trust_score_min: float = 50.0
    trust_score_max: float = 70.0
    min_orders: int = 5
    max_seller_age_days: int = 90


@dataclass
class HealthyThresholds:
    """Thresholds for HEALTHY tier (no action needed)."""
    return_rate_max: float = 0.08
    negative_review_rate_max: float = 0.05
    late_delivery_rate_max: float = 0.04
    cancellation_rate_max: float = 0.025
    trust_score_min: float = 70.0
    anomaly_count_max: int = 0


@dataclass
class ActionThresholds:
    """Complete action threshold configuration."""
    escalate: EscalateThresholds = field(default_factory=EscalateThresholds)
    coach: CoachThresholds = field(default_factory=CoachThresholds)
    monitor: MonitorThresholds = field(default_factory=MonitorThresholds)
    healthy: HealthyThresholds = field(default_factory=HealthyThresholds)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionThresholds":
        """Create ActionThresholds from dictionary (e.g., loaded from JSON)."""
        return cls(
            escalate=EscalateThresholds(**data.get("escalate", {})),
            coach=CoachThresholds(**data.get("coach", {})),
            monitor=MonitorThresholds(**data.get("monitor", {})),
            healthy=HealthyThresholds(**data.get("healthy", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "escalate": vars(self.escalate),
            "coach": vars(self.coach),
            "monitor": vars(self.monitor),
            "healthy": vars(self.healthy),
        }

    @classmethod
    def load_from_file(cls, path: str | Path) -> "ActionThresholds":
        """Load thresholds from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_to_file(self, path: str | Path) -> None:
        """Save thresholds to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# Default thresholds instance
DEFAULT_THRESHOLDS = ActionThresholds()


def assign_action_tier(
    seller_metrics: dict[str, Any],
    thresholds: ActionThresholds = DEFAULT_THRESHOLDS,
) -> str:
    """
    Assign action tier to a seller based on their metrics.

    Args:
        seller_metrics: Dictionary with seller metrics including:
            - return_rate (float)
            - negative_review_rate (float)
            - late_delivery_rate (float)
            - cancellation_rate (float)
            - trust_score (float or None)
            - anomaly_count (int)
            - declining_trend (bool)
            - total_orders (int)
            - seller_age_days (int, optional)
        thresholds: ActionThresholds configuration

    Returns:
        Tier name: "escalate", "coach", "monitor", or "healthy"
    """
    # Extract metrics with defaults
    return_rate = seller_metrics.get("return_rate", 0.0)
    negative_review_rate = seller_metrics.get("negative_review_rate", 0.0)
    late_delivery_rate = seller_metrics.get("late_delivery_rate", 0.0)
    cancellation_rate = seller_metrics.get("cancellation_rate", 0.0)
    trust_score = seller_metrics.get("trust_score")
    anomaly_count = seller_metrics.get("anomaly_count", 0)
    declining_trend = seller_metrics.get("declining_trend", False)
    total_orders = seller_metrics.get("total_orders", 0)
    seller_age_days = seller_metrics.get("seller_age_days", 999)

    # Handle missing trust score (ineligible sellers)
    if trust_score is None or (isinstance(trust_score, float) and trust_score != trust_score):  # NaN check
        trust_score = 0.0

    # Check ESCALATE (most restrictive first)
    e = thresholds.escalate
    if (return_rate > e.return_rate or
        negative_review_rate > e.negative_review_rate or
        late_delivery_rate > e.late_delivery_rate or
        cancellation_rate > e.cancellation_rate or
        trust_score < e.trust_score_max or
        anomaly_count >= e.anomaly_count_min):
        return "escalate"

    # Check COACH
    c = thresholds.coach
    coach_conditions = [
        c.return_rate_min <= return_rate <= c.return_rate_max,
        c.negative_review_rate_min <= negative_review_rate <= c.negative_review_rate_max,
        c.late_delivery_rate_min <= late_delivery_rate <= c.late_delivery_rate_max,
        c.cancellation_rate_min <= cancellation_rate <= c.cancellation_rate_max,
        c.trust_score_min <= trust_score <= c.trust_score_max,
        c.anomaly_count_min <= anomaly_count <= c.anomaly_count_max,
    ]
    if c.declining_trend:
        coach_conditions.append(declining_trend)

    if any(coach_conditions):
        return "coach"

    # Check MONITOR
    m = thresholds.monitor
    monitor_conditions = [
        m.return_rate_min <= return_rate <= m.return_rate_max,
        m.negative_review_rate_min <= negative_review_rate <= m.negative_review_rate_max,
        m.late_delivery_rate_min <= late_delivery_rate <= m.late_delivery_rate_max,
        m.cancellation_rate_min <= cancellation_rate <= m.cancellation_rate_max,
        m.trust_score_min <= trust_score <= m.trust_score_max,
        total_orders < m.min_orders,
        seller_age_days < m.max_seller_age_days,
    ]

    if any(monitor_conditions):
        return "monitor"

    # Default to HEALTHY
    return "healthy"


def assign_action_tiers_batch(
    sellers_df,
    thresholds: ActionThresholds = DEFAULT_THRESHOLDS,
):
    """
    Assign action tiers to multiple sellers.

    Args:
        sellers_df: DataFrame with seller metrics
        thresholds: ActionThresholds configuration

    Returns:
        Series with action tier for each seller
    """
    return sellers_df.apply(lambda row: assign_action_tier(row.to_dict(), thresholds), axis=1)


def get_tier_recommendations(tier: str) -> dict[str, Any]:
    """Get recommended actions for a given tier."""
    recommendations = {
        "escalate": {
            "priority": "CRITICAL",
            "actions": [
                "Immediate account review by trust & safety team",
                "Potential temporary suspension",
                "Mandatory improvement plan with 30-day deadline",
                "Daily monitoring of key metrics",
                "Direct communication with seller",
            ],
            "review_frequency": "daily",
        },
        "coach": {
            "priority": "HIGH",
            "ac
