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


if __name__ == "__main__":
    unittest.main()
