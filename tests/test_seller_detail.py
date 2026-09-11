import unittest

from app.seller_detail import build_seller_detail, seller_detail_csv
from tests.test_seller_report import sample_fact, sample_metrics


class SellerDetailTests(unittest.TestCase):
    def test_detail_combines_report_signals_and_downloads(self):
        detail = build_seller_detail(sample_metrics(), sample_fact(), "s1")
        self.assertEqual(detail["report"]["seller_id"], "s1")
        self.assertIn("delivery_contribution", detail["signals"].columns)
        self.assertIn(b"seller_id", seller_detail_csv(detail))
        self.assertIn("Seller Health Report", detail["html"])

    def test_unknown_seller_is_explained(self):
        with self.assertRaisesRegex(ValueError, "not available"):
            build_seller_detail(sample_metrics(), sample_fact(), "unknown")


if __name__ == "__main__":
    unittest.main()
