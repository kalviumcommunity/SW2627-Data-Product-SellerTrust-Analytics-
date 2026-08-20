import unittest

import pandas as pd

from src.data_quality import add_delivery_features, flag_iqr_outliers, validate_order_timeline


class DataQualityTests(unittest.TestCase):
    def setUp(self):
        self.orders = pd.DataFrame(
            {
                "order_purchase_timestamp": ["2018-01-01", "2018-01-02"],
                "order_approved_at": ["2018-01-01 02:00", "2018-01-02 02:00"],
                "order_delivered_carrier_date": ["2018-01-02", "2018-01-03"],
                "order_delivered_customer_date": ["2018-01-10", "2018-01-04"],
                "order_estimated_delivery_date": ["2018-01-08", "2018-01-05"],
            }
        )

    def test_delivery_features_preserve_late_delivery_direction(self):
        result = add_delivery_features(self.orders)
        self.assertEqual(result.loc[0, "delivery_delay_days"], 2)
        self.assertTrue(result.loc[0, "is_late_delivery"])
        self.assertFalse(result.loc[1, "is_late_delivery"])

    def test_timeline_validation_reports_impossible_dates(self):
        invalid = self.orders.copy()
        invalid.loc[0, "order_delivered_customer_date"] = "2017-12-31"
        results = {item.rule: item for item in validate_order_timeline(invalid)}
        self.assertFalse(results["delivery_after_purchase"].passed)
        self.assertEqual(results["delivery_after_purchase"].failed_rows, 1)

    def test_iqr_outliers_are_flagged_and_retained(self):
        result = flag_iqr_outliers(pd.DataFrame({"days": [1, 2, 2, 3, 40]}), "days")
        self.assertEqual(len(result), 5)
        self.assertTrue(result.loc[4, "days_outlier"])


if __name__ == "__main__":
    unittest.main()
