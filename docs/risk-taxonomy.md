# Seller Risk Taxonomy

The canonical seller `risk_tier` is a score band derived from the final trust
score. It is used consistently in pipeline outputs, Parquet files, SQLite
views, dashboard filters, segments, comparisons, and seller reports.

| Trust score | Risk tier |
|-------------|-----------|
| 0-45        | High-Risk |
| >45-60      | Return-Prone |
| >60-75      | Inconsistent |
| >75-100     | Reliable |
| Missing or ineligible | Insufficient Data |

`recommended_action` is intentionally separate from `risk_tier`. It describes
the operational response and can be `Escalate`, `Coach`, `Monitor`, or `No
Action`, based on the score, anomalies, and configured signal thresholds.
