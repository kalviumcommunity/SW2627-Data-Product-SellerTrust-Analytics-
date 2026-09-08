from __future__ import annotations

from collections.abc import MutableMapping
from datetime import datetime

FILTER_DEFAULTS = {
    "seller_search": "",
    "selected_risk_tier": "All",
    "selected_category": "All",
}
LAST_REFRESHED_KEY = "last_data_refreshed_at"


def initialise_filter_state(session_state: MutableMapping) -> None:
    """Populate missing Streamlit session-state keys for persistent filters."""
    for key, value in FILTER_DEFAULTS.items():
        session_state.setdefault(key, value)
    session_state.setdefault(LAST_REFRESHED_KEY, None)


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


def mark_data_refreshed(
    session_state: MutableMapping,
    refreshed_at: datetime | None = None,
) -> datetime:
    """Store the latest successful dashboard refresh timestamp."""
    timestamp = refreshed_at or datetime.now().astimezone()
    session_state[LAST_REFRESHED_KEY] = timestamp
    return timestamp


def get_last_refresh_label(session_state: MutableMapping) -> str:
    """Return a display label for the last successful dashboard refresh."""
    timestamp = session_state.get(LAST_REFRESHED_KEY)
    if timestamp is None:
        return "Last refreshed: Not refreshed this session"
    if isinstance(timestamp, str):
        return f"Last refreshed: {timestamp}"
    return f"Last refreshed: {timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}"
