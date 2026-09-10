from __future__ import annotations

import plotly.graph_objects as go

TRUSTED_GREEN = "#2ca02c"
WATCHLIST_YELLOW = "#ffbf00"
HIGH_RISK_RED = "#d62728"
NEUTRAL_GREY = "#8c8c8c"

RISK_TIER_COLORS = {
    "Reliable": TRUSTED_GREEN,
    "Trusted": TRUSTED_GREEN,
    "Inconsistent": WATCHLIST_YELLOW,
    "Return-Prone": WATCHLIST_YELLOW,
    "Watchlist": WATCHLIST_YELLOW,
    "High-Risk": HIGH_RISK_RED,
    "High Risk": HIGH_RISK_RED,
    "Insufficient Data": NEUTRAL_GREY,
}

SENTIMENT_COLORS = {
    "positive": TRUSTED_GREEN,
    "Positive": TRUSTED_GREEN,
    "neutral": WATCHLIST_YELLOW,
    "Neutral": WATCHLIST_YELLOW,
    "negative": HIGH_RISK_RED,
    "Negative": HIGH_RISK_RED,
}


def apply_chart_polish(
    fig: go.Figure,
    *,
    height: int = 420,
    showlegend: bool | None = None,
    bottom_margin: int = 55,
) -> go.Figure:
    """Apply shared dashboard chart styling and responsive label spacing."""
    layout_args: dict[str, object] = {
        "height": height,
        "template": "plotly_white",
        "margin": {"l": 30, "r": 24, "t": 64, "b": bottom_margin},
        "hovermode": "closest",
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        "uniformtext_minsize": 10,
        "uniformtext_mode": "hide",
    }
    if showlegend is not None:
        layout_args["showlegend"] = showlegend

    fig.update_layout(**layout_args)
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    return fig

