import unittest
from datetime import UTC, datetime

from app.ui_state import (
    FILTER_DEFAULTS,
    LAST_REFRESHED_KEY,
    get_last_refresh_label,
    initialise_filter_state,
    mark_data_refreshed,
    normalise_selected_option,
)


class UiStateTests(unittest.TestCase):
    def test_initialise_filter_state_populates_missing_filter_keys(self):
        session_state = {}

        initialise_filter_state(session_state)

        for key, value in FILTER_DEFAULTS.items():
            self.assertEqual(session_state[key], value)
        self.assertIsNone(session_state[LAST_REFRESHED_KEY])

    def test_initialise_filter_state_preserves_existing_values(self):
        session_state = {"seller_search": "abc"}

        initialise_filter_state(session_state)

        self.assertEqual(session_state["seller_search"], "abc")
        self.assertEqual(session_state["selected_risk_tier"], "All")

    def test_normalise_selected_option_keeps_valid_selection(self):
        session_state = {"selected_category": "books"}

        result = normalise_selected_option(
            session_state,
            "selected_category",
            ["All", "books"],
        )

        self.assertEqual(result, "books")
        self.assertEqual(session_state["selected_category"], "books")

    def test_normalise_selected_option_resets_invalid_selection(self):
        session_state = {"selected_category": "toys"}

        result = normalise_selected_option(
            session_state,
            "selected_category",
            ["All", "books"],
        )

        self.assertEqual(result, "All")
        self.assertEqual(session_state["selected_category"], "All")

    def test_mark_data_refreshed_stores_timestamp(self):
        session_state = {}
        timestamp = datetime(2026, 9, 8, 9, 30, tzinfo=UTC)

        result = mark_data_refreshed(session_state, timestamp)

        self.assertEqual(result, timestamp)
        self.assertEqual(session_state[LAST_REFRESHED_KEY], timestamp)

    def test_get_last_refresh_label_handles_missing_timestamp(self):
        self.assertEqual(
            get_last_refresh_label({}),
            "Last refreshed: Not refreshed this session",
        )

    def test_get_last_refresh_label_formats_timestamp(self):
        timestamp = datetime(2026, 9, 8, 9, 30, 15, tzinfo=UTC)

        label = get_last_refresh_label({LAST_REFRESHED_KEY: timestamp})

        self.assertIn("Last refreshed: 2026-09-08 09:30:15", label)


if __name__ == "__main__":
    unittest.main()
