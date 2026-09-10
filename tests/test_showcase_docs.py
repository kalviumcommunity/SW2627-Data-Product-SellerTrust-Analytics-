import unittest
from pathlib import Path


class ShowcaseDocumentationTests(unittest.TestCase):
    def test_showcase_walkthrough_covers_required_sections(self):
        doc = Path("docs/dashboard-showcase-walkthrough.md").read_text()

        for section in [
            "Trust Overview",
            "Trust vs. Behaviour Signals",
            "Seller Scorecard",
            "Behaviour Segments",
            "Trust-Risk Actions",
        ]:
            self.assertIn(section, doc)

    def test_showcase_walkthrough_acknowledges_limitations_and_recording(self):
        doc = Path("docs/dashboard-showcase-walkthrough.md").read_text()

        self.assertIn("Recording Checklist", doc)
        self.assertIn("3-5 minutes", doc)
        self.assertIn("static historical dataset", doc)
        self.assertIn("cancellation-rate proxy", doc)
        self.assertIn("score-bucketed", doc)


if __name__ == "__main__":
    unittest.main()

