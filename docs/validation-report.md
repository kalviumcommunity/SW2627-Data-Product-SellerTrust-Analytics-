# End-to-End Data Validation Report

## Pipeline Execution Summary
- Date: 2026-09-04
- Raw Data Source: Olist v1 CSVs (5 files)
- Pipeline Status: SUCCESS

## Row Counts at Each Stage
| Stage | Row Count |
|-------|-----------|
| Raw Orders (olist_orders_dataset.csv) | 100,010 |
| Seller-Order Fact Table | 100,010 |
| Seller Metrics (aggregated) | 3,095 |
| Sellers with Trust Score | 1,794 |
| Sellers without Trust Score (ineligible) | 1,301 |

## Data Quality Checks

### NULL Value Analysis
- **late_delivery_rate**: PASS
- **average_review_score**: 5 NULLs
- **cancellation_rate_proxy**: PASS
- **negative_review_rate**: PASS
- **trust_score (eligible sellers)**: PASS - No NULLs for eligible sellers
- **trust_score (ineligible sellers)**: PASS - All correctly NULL

### Trust Score Distribution
- Mean: 88.01
- Median: 89.06
- Min: 40.00
- Max: 100.00
- Std Dev: 7.68

### Eligibility Check
- Eligible (>=5 orders): 1,794 (58.0%)
- Ineligible (<5 orders): 1,301 (42.0%)

## Anomaly Detection Summary
- Sellers with any anomaly: 780 of 3,095 (25.2%)

## Trend Detection Summary
- Declining trend: 76
- Improving trend: 73
- Stable: 1,638
- Insufficient data: 1,303

## Overall Validation Result
ALL CHECKS PASSED - Pipeline executed successfully, all 3,095 sellers processed, trust scores computed for eligible sellers.
