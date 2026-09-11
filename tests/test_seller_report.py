"""Tests for the single-seller health report (issue #46)."""

import unittest

import numpy as np
import pandas as pd

from src.seller_report import (
    SellerNotFoundError,
    build_history_chart,
    collect_seller_report,
    format_value,
    render_report,
)


def sample_metrics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "seller_id": "s1",
                "total_orders": 20,
                "delivered_orders_with_dates": 9,
                "cancelled_orders": 0,
                "average_review_score": 1.26,
                "negative_review_rate": 0.947,
                "average_response_time_hours": 44.6,
                "late_delivery_rate": 0.5,
                "average_delivery_delay_days": -5.6,
                "cancellation_rate_proxy": 0.0,
                "eligible_for_risk_score": True,
                "trust_score": 38.03,
                "risk_tier": "ESCALATE",
            },
            {
                "seller_id": "s2",
                "total_orders": 2,
                "delivered_orders_with_dates": 0,
                "cancelled_orders": 2,
                "average_review_score": np.nan,
                "negative_review_rate": np.nan,
                "average_response_time_hours": np.nan,
                "late_delivery_rate": 0.0,
                "average_delivery_delay_days": np.nan,
                "cancellation_rate_proxy": 1.0,
                "eligible_for_risk_score": False,
                "trust_score": np.nan,
                "risk_tier": "ESCALATE",
            },
        ]
    )


def sample_fact() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "seller_id": "s1",
                "order_id": f"o{i}",
                "order_purchase_timestamp": f"2018-0{1 + i % 3}-10",
                "review_score": 1 + i % 3,
                "is_late_delivery": i % 2 == 0,
            }
            for i in range(9)
        ]
    )


class FormatValueTests(unittest.TestCase):
    def test_missing_values_read_as_not_available(self):
        """'n/a' and '0.0%' must never be confused — that distinction is the point."""
        self.assertEqual(format_value(np.nan, "pct"), "n/a")
        self.assertEqual(format_value(None, "days"), "n/a")
        self.assertEqual(format_value(0.0, "pct"), "0.0%")

    def test_delay_direction_is_spelled_out(self):
        self.assertIn("early", format_value(-5.6, "days"))
        self.assertIn("late", format_value(3.2, "days"))


class CollectReportTests(unittest.TestCase):
    def test_unknown_seller_raises(self):
        with self.assertRaises(SellerNotFoundError):
            collect_seller_report("nobody", metrics=sample_metrics(), fact=sample_fact())

    def test_report_carries_metrics_and_history(self):
        report = collect_seller_report("s1", metrics=sample_metrics(), fact=sample_fact())
        self.assertEqual(report["seller_id"], "s1")
        self.assertAlmostEqual(report["trust_score"], 38.03)
        self.assertEqual(report["risk_tier"], "ESCALATE")
        self.assertEqual(
            {m["key"] for m in report["metrics"]} & {"trust_score", "late_delivery_rate"},
            {"trust_score", "late_delivery_rate"},
        )
        self.assertEqual(len(report["history"]), 3)

    def test_ineligible_seller_is_flagged_not_silently_scored(self):
        report = collect_seller_report("s2", metrics=sample_metrics(), fact=sample_fact())
        self.assertFalse(report["eligible"])
        self.assertIsNone(report["trust_score"])
        self.assertIn("5-order floor", report["eligibility_note"])
        self.assertIn("late-delivery rate is unknown", report["eligibility_note"])

    def test_trend_defaults_to_insufficient_data_without_a_trends_file(self):
        report = collect_seller_report("s1", metrics=sample_metrics(), fact=sample_fact())
        self.assertEqual(report["trend"]["flag"], "insufficient_data")

    def test_trend_is_read_when_supplied(self):
        trends = pd.DataFrame([{"seller_id": "s1", "slope": -0.002, "p_value": 0.01, "trend_flag": "declining"}])
        report = collect_seller_report("s1", metrics=sample_metrics(), fact=sample_fact(), trends=trends)
        self.assertEqual(report["trend"]["flag"], "declining")
        self.assertEqual(report["trend"]["label"], "Declining")

    def test_anomaly_metrics_are_named_once_each(self):
        """Three columns per metric must not produce three list entries for one metric."""
        anomalies = pd.DataFrame(
            [
                {
                    "seller_id": "s1",
                    "late_delivery_rate_iqr_outlier": True,
                    "late_delivery_rate_zscore_anomaly": True,
                    "late_delivery_rate_anomaly": True,
                    "average_review_score_iqr_outlier": False,
                    "average_review_score_zscore_anomaly": False,
                    "average_review_score_anomaly": False,
                    "any_anomaly": True,
                    "is_anomaly": True,
                    "anomaly_count": 2,
                }
            ]
        )
        report = collect_seller_report("s1", metrics=sample_metrics(), fact=sample_fact(), anomalies=anomalies)
        self.assertEqual(report["anomaly_count"], 2)
        self.assertEqual(report["anomaly_metrics"], ["late delivery rate (IQR, z-score)"])

    def test_actions_supply_the_recommendation_and_evidence(self):
        actions = pd.DataFrame(
            [
                {
                    "seller_id": "s1",
                    "recommended_action": "Escalate",
                    "evidence": ["Late delivery rate is 50% (high)", "Average review score is 1.3/5.0 (very low)"],
                }
            ]
        )
        report = collect_seller_report("s1", metrics=sample_metrics(), fact=sample_fact(), actions=actions)
        self.assertEqual(report["recommended_action"], "Escalate")
        self.assertEqual(len(report["evidence"]), 2)


class RenderTests(unittest.TestCase):
    def test_rendered_html_contains_the_headline_facts(self):
        report = collect_seller_report("s1", metrics=sample_metrics(), fact=sample_fact())
        html = render_report(report)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("s1", html)
        self.assertIn("38.0", html)
        self.assertIn("ESCALATE", html)
        self.assertIn("50.0%", html)

    def test_missing_metrics_render_as_not_available(self):
        report = collect_seller_report("s2", metrics=sample_metrics(), fact=sample_fact())
        html = render_report(report)
        self.assertIn("n/a", html)
        self.assertIn("5-order floor", html)

    def test_chart_is_embedded_when_there_is_history(self):
        report = collect_seller_report("s1", metrics=sample_metrics(), fact=sample_fact())
        chart = build_history_chart(report["history"], "s1")
        self.assertIn("plotly", chart.lower())
        self.assertIn(chart, render_report(report, chart))

    def test_chart_is_skipped_for_a_single_month(self):
        """One point is not a trend line; the section should not appear at all."""
        self.assertEqual(
            build_history_chart(
                [{"month": "2018-01", "orders": 5, "average_review_score": 4.0, "late_delivery_rate": 0.1}], "s1"
            ),
            "",
        )


if __name__ == "__main__":
    unittest.main()
