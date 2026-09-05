from __future__ import annotations

from collections.abc import MutableMapping

FILTER_DEFAULTS = {
    "seller_search": "",
    "selected_risk_tier": "All",
    "selected_category": "All",
}


def initialise_filter_state(session_state: MutableMapping) -> None:
    """Populate missing Streamlit session-state keys for persistent filters."""
    for key, value in FILTER_DEFAULTS.items():
        session_state.setdefault(key, value)


def normalise_selected_option(
    session_state: MutableMapping,
    key: str,
    valid_options: list[str],
    fallback: str = "All",
) -> str:
    """Keep a session-state selection valid when option lists change."""
    current_value = session_state.get(key, fallback)
    if current_value not in valid_options:
        session_state[key] = fallback
        return fallback
    return current_value
