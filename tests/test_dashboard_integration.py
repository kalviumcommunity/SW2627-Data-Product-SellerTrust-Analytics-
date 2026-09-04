import unittest
from pathlib import Path


class DashboardIntegrationTests(unittest.TestCase):
    def test_main_app_exposes_all_five_dashboard_sections(self):
        app_source = Path("app/main.py").read_text()

        for section in [
            "Trust Overview",
            "Trust vs. Behaviour Signals",
            "Seller Scorecard",
            "Behaviour Segments",
            "Trust-Risk Actions",
        ]:
            self.assertIn(section, app_source)

    def test_main_app_imports_each_dashboard_module(self):
        app_source = Path("app/main.py").read_text()

        for module in [
            "app.actions",
            "app.filters",
            "app.overview",
            "app.scorecard",
            "app.segments",
            "app.signals",
        ]:
            self.assertIn(module, app_source)

    def test_main_app_uses_loading_spinners_and_session_state_filters(self):
        app_source = Path("app/main.py").read_text()

        self.assertIn("initialise_filter_state(st.session_state)", app_source)
        self.assertIn("st.spinner", app_source)
        self.assertIn('key="seller_search"', app_source)
        self.assertIn('key="selected_risk_tier"', app_source)
        self.assertIn('key="selected_category"', app_source)

    def test_main_app_has_edge_case_messages(self):
        app_source = Path("app/main.py").read_text()

        self.assertIn("No sellers match the selected filters.", app_source)
        self.assertIn("Dashboard data is not available yet.", app_source)
        self.assertIn("Generate data/processed/seller_metrics.csv", app_source)


if __name__ == "__main__":
    unittest.main()
