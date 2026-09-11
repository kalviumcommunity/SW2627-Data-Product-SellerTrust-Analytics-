from __future__ import annotations

import pandas as pd

from app.theme import HIGH_RISK_RED, TRUSTED_GREEN, WATCHLIST_YELLOW
from src.actions import ACTION_COACH, ACTION_ESCALATE, ACTION_MONITOR, recommend_actions

SEVERITY_STYLES = {
    ACTION_ESCALATE: {
        "label": "High Severity",
        "color": HIGH_RISK_RED,
        "badge": "🔴 Escalate",
    },
    ACTION_COACH: {
        "label": "Medium Severity",
        "color": WATCHLIST_YELLOW,
        "badge": "🟡 Coach",
    },
    ACTION_MONITOR: {
        "label": "Low Severity",
        "color": TRUSTED_GREEN,
        "badge": "🟢 Monitor",
    },
}

ACTION_SORT_ORDER = {
    ACTION_ESCALATE: 0,
    ACTION_COACH: 1,
    ACTION_MONITOR: 2,
}


def build_action_cards(metrics: pd.DataFrame) -> pd.DataFrame:
    """Prepare flagged seller action-card data for the dashboard."""
    recommendations = recommend_actions(metrics)
    flagged = recommendations[recommendations["recommended_action"].isin(SEVERITY_STYLES)].copy()
    flagged["severity_label"] = flagged["recommended_action"].map(lambda action: SEVERITY_STYLES[action]["label"])
    flagged["severity_color"] = flagged["recommended_action"].map(lambda action: SEVERITY_STYLES[action]["color"])
    flagged["action_badge"] = flagged["recommended_action"].map(lambda action: SEVERITY_STYLES[action]["badge"])
    flagged["severity_rank"] = flagged["recommended_action"].map(ACTION_SORT_ORDER)
    return flagged.sort_values(
        ["severity_rank", "trust_score"],
        ascending=[True, True],
    ).drop(columns=["severity_rank"])


def build_action_queue(
    metrics: pd.DataFrame,
    action: str = "All",
    sort_by: str = "Severity",
    ascending: bool = True,
) -> pd.DataFrame:
    """Return the complete flagged queue with dashboard-friendly controls applied."""
    queue = build_action_cards(metrics)
    if action != "All":
        queue = queue[queue["recommended_action"] == action]
    sort_columns = {
        "Severity": ["severity_rank", "trust_score"],
        "Trust Score": ["trust_score"],
        "Total Orders": ["total_orders"],
        "Seller ID": ["seller_id"],
    }
    queue = queue.copy()
    queue["severity_rank"] = queue["recommended_action"].map(ACTION_SORT_ORDER)
    columns = sort_columns.get(sort_by, sort_columns["Severity"])
    return queue.sort_values(columns, ascending=ascending, na_position="last").drop(columns=["severity_rank"])


def paginate_action_queue(queue: pd.DataFrame, page: int, page_size: int = 20) -> pd.DataFrame:
    """Return one one-based page from an action queue."""
    if page_size <= 0 or page <= 0:
        raise ValueError("page and page_size must be positive")
    start = (page - 1) * page_size
    return queue.iloc[start : start + page_size]


def action_queue_export(metrics: pd.DataFrame) -> pd.DataFrame:
    """Return every recommendation in a CSV-safe form for complete export."""
    recommendations = recommend_actions(metrics).copy()
    recommendations["evidence"] = recommendations["evidence"].map(
        lambda items: " | ".join(format_evidence_bullets(items))
    )
    return recommendations


def format_evidence_bullets(evidence: list[str] | str) -> list[str]:
    """Normalize recommendation evidence into displayable bullet text."""
    if isinstance(evidence, list):
        return evidence
    if not isinstance(evidence, str) or not evidence.strip():
        return []
    return [item.strip() for item in evidence.split("|") if item.strip()]
