from __future__ import annotations

import pandas as pd

from src.actions import ACTION_COACH, ACTION_ESCALATE, ACTION_MONITOR, recommend_actions


SEVERITY_STYLES = {
    ACTION_ESCALATE: {
        "label": "High Severity",
        "color": "#d62728",
        "badge": "🔴 Escalate",
    },
    ACTION_COACH: {
        "label": "Medium Severity",
        "color": "#ffbf00",
        "badge": "🟡 Coach",
    },
    ACTION_MONITOR: {
        "label": "Low Severity",
        "color": "#2ca02c",
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
    flagged = recommendations[
        recommendations["recommended_action"].isin(SEVERITY_STYLES)
    ].copy()
    flagged["severity_label"] = flagged["recommended_action"].map(
        lambda action: SEVERITY_STYLES[action]["label"]
    )
    flagged["severity_color"] = flagged["recommended_action"].map(
        lambda action: SEVERITY_STYLES[action]["color"]
    )
    flagged["action_badge"] = flagged["recommended_action"].map(
        lambda action: SEVERITY_STYLES[action]["badge"]
    )
    flagged["severity_rank"] = flagged["recommended_action"].map(ACTION_SORT_ORDER)
    return flagged.sort_values(
        ["severity_rank", "trust_score"],
        ascending=[True, True],
    ).drop(columns=["severity_rank"])


def format_evidence_bullets(evidence: list[str] | str) -> list[str]:
    """Normalize recommendation evidence into displayable bullet text."""
    if isinstance(evidence, list):
        return evidence
    if not isinstance(evidence, str) or not evidence.strip():
        return []
    return [item.strip() for item in evidence.split("|") if item.strip()]
