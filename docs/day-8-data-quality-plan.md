# Day 8 — Date Pipeline, Outliers & Validation

This contribution implements Modules 2.22–2.24 for the Seller Trust Analytics project.

## Date and time pipeline

`src/data_quality.py` parses Olist order timestamps with invalid values coerced to null, then derives:

| Field | Formula | Interpretation |
|---|---|---|
| `delivery_delay_days` | delivered customer date − estimated delivery date | Positive values are late deliveries. |
| `is_late_delivery` | `delivery_delay_days > 0` | Late-delivery signal for the seller risk score. |
| `order_age_days` | estimated delivery date − purchase timestamp | Expected end-to-end delivery window. |
| `purchase_month` | purchase timestamp grouped by month | Supports monthly trend charts. |

Missing delivery dates are retained as missing. They must not be treated as an on-time delivery.

## Outlier treatment

Delivery delays and later seller-level metrics can be marked with `flag_iqr_outliers`. The method uses the standard 1.5 × IQR fence. It **flags rather than deletes** unusual records, because extreme delays can be genuine trust-risk evidence.

## Validation rules

The pipeline checks these temporal rules before producing dashboard-ready data:

1. Approval must not occur before purchase.
2. Carrier handoff must not occur before purchase.
3. Customer delivery must not occur before purchase.
4. Customer delivery must not occur before carrier handoff.

Rows with missing optional timestamps are not marked invalid by these comparisons; they remain visible in completeness reporting. A failed rule stops `require_valid_orders` with the rule name and failed-row count.

## Visualisation hand-off

Use `delivery_delay_days` for the Day 8 box plot and `is_late_delivery` for seller/cohort scatter-plot colouring. Keep outlier flags visible in hover text or a table filter rather than silently excluding them.
