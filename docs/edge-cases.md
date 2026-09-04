# Edge Cases in Data Processing

**Issue:** #31 - Document edge cases in data processing  
**Date:** 2026-09-04  
**Analysis based on:** Olist v1 dataset (100,010 orders, 3,095 sellers)

---

## Identified Edge Cases

### 1. Sellers with 0 Reviews
- **Count:** 5 sellers
- **Impact:** These sellers have orders but no review_score in the fact table
- **Current Handling:** Excluded from review-based metrics (average_review_score, negative_review_rate become NaN)
- **Trust Score:** These sellers get NULL trust_score if they have <5 orders, or NaN review components if eligible

### 2. Sellers with ALL Cancelled Orders
- **Count:** 39 sellers
- **Impact:** All their orders are cancelled; no delivery metrics available
- **Current Handling:** 
  - `late_delivery_rate` = NaN (no delivered orders)
  - `cancellation_rate_proxy` = 1.0 (100%)
  - `average_review_score` = NaN (no reviews on cancelled orders)
  - Trust score: NULL if <5 orders, or heavily penalized by cancellation_rate_proxy

### 3. Missing Delivery Timestamps
| Field | Missing Count | % of Orders |
|-------|--------------|-------------|
| order_delivered_carrier_date | 1,010 | ~1.0% |
| order_delivered_customer_date | 2,193 | ~2.2% |
| order_estimated_delivery_date | 0 | 0% |

- **Impact:** Cannot compute `delivery_delay_days` or `is_late_delivery` for these orders
- **Current Handling:** Rows with missing timestamps get NaN for delivery delay metrics; excluded from late delivery rate calculation

### 4. Orders Missing Review Scores
- **Count:** 763 orders (out of ~99,247 delivered orders)
- **Impact:** Cannot compute review-based metrics for these orders
- **Current Handling:** Excluded from `average_review_score`, `negative_review_rate`, and `sentiment_bucket` calculations

### 5. Ineligible Sellers (<5 Orders)
- **Count:** 1,301 sellers (42.0% of all sellers)
- **Impact:** Not statistically stable enough for trust scoring
- **Current Handling:** `eligible_for_risk_score = False`, trust_score = NULL/NaN

### 6. Early Deliveries (Negative Delivery Delay)
- **Count:** 89,972 orders (90.0% of all orders!)
- **Impact:** Most orders delivered before estimated date; negative delay days
- **Current Handling:** Treated as "not late" (`is_late_delivery = False`), negative delay included in average calculations

### 7. Zero/Negative Freight Values
- **Count:** 338 orders with freight_value <= 0 (freight_value), 0 with item_value <= 0
- **Impact:** Free shipping or data entry errors
- **Current Handling:** Included in aggregations; freight_value=0 treated as valid free shipping

### 8. Duplicate Order-Seller Combinations
- **Count:** 0 duplicates found
- **Status:** No duplicates in seller-order fact table

### Additional Edge Cases Identified

#### Missing Delivery Carrier Date (1,010 orders)
Orders where carrier picked up but customer delivery date missing - affects late delivery calculation.

#### Missing Customer Delivery Date (2,193 orders)  
Orders marked delivered to carrier but not yet to customer - affects delivery delay calculation.

#### Free Shipping (Freight = 0)
338 orders with freight_value = 0 - likely promotional free shipping.

#### Single Order Sellers (571 sellers)
Sellers with exactly 1 order - high variance in metrics.

---

## Code Handling Verification

| Edge Case | Code Location | Handled? |
|-----------|---------------|----------|
| Missing timestamps | `src/data_quality.py:add_delivery_features()` | Yes - Coerces to NaT, computes delay only when both dates present |
| Missing review scores | `src/pipeline.py:build_seller_order_fact()` | Yes - Left as NaN, excluded from mean calculations |
| Ineligible sellers (<5 orders) | `src/pipeline.py:build_seller_metrics()` + `src/trust_score.py` | Yes - Flagged with `eligible_for_risk_score`, trust_score = NULL |
| All-cancelled sellers | Pipeline aggregation | Partial - Review metrics become NaN, cancellation_rate_proxy = 1.0 |
| Early deliveries (negative delay) | `src/data_quality.py` + trust score calc | Partial - Treated as not late; negative values reduce average delay |

---

## Recommendations for Improvement

### High Priority
1. **Add explicit handling for all-cancelled sellers** - Consider separate risk tier or flagging logic since their metrics are degenerate.

2. **Document early delivery bias** - The fact that ~90% of deliveries are "early" suggests the estimated delivery date is conservative. Consider adjusting the benchmark or using a different metric.

3. **Add data quality flags** - Add boolean columns to fact table indicating:
   - `has_valid_delivery_dates`
   - `has_review`
   - `is_cancelled`

### Medium Priority  
4. **Review free shipping detection** - freight_value=0 could be free shipping promo vs data error.

5. **Consider minimum order threshold per metric** - Some metrics need more than just total_orders >=5 to be reliable.

---

## Test Coverage Gaps

The following edge cases should have explicit unit tests:
- [ ] Seller with all cancelled orders gets correct cancellation_rate_proxy = 1.0 and NULL review metrics
- [ ] Order with missing delivery timestamps gets NaN delay and is excluded from late rate
- [ ] Seller with exactly 5 orders is eligible; seller with <5 is not
- [ ] Negative delivery delays don't break trust score calculation

---

## Summary

The pipeline handles most edge cases gracefully by:
1. Using pandas' native NaN propagation for missing data
2. Filtering ineligible sellers before trust scoring  
3. Computing aggregations only on valid data subsets

Key areas needing attention: all-cancelled seller handling and the early-delivery bias in estimated dates.
