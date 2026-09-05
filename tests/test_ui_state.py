import unittest

from app.ui_state import (
    FILTER_DEFAULTS,
    initialise_filter_state,
    normalise_selected_option,
)


class UiStateTests(unittest.TestCase):
    def test_initialise_filter_state_populates_missing_filter_keys(self):
        session_state = {}

        initialise_filter_state(session_state)

        self.assertEqual(session_state, FILTER_DEFAULTS)

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


if __name__ == "__main__":
    unittest.main()
