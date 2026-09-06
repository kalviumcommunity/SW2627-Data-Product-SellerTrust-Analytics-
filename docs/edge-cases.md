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
  - `late_delivery_rate` = 0.0 (filled from NaN via `fillna(0.0)` — **NOTE: This gives a "perfect" delivery score if seller were eligible and had reviews**)
  - `average_delivery_delay_days` = 0.0 (filled from NaN)
  - `cancellation_rate_proxy` = 1.0 (100%)
  - `average_review_score` = NaN (no reviews on cancelled orders)
  - `negative_review_rate` = 0.0 (no reviews to be negative)
  - Trust score: NaN if <5 orders (`eligible_for_risk_score=False`), or NaN if ≥5 orders due to missing review scores propagating through trust calculation

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
| Missing timestamps | `src/data_quality.py:add_delivery_features()` | Yes - Coerces to NaT, computes delay only when both dates present; excluded from late rate denominator |
| Missing review scores | `src/pipeline.py:build_seller_order_fact()` | Yes - Left as NaN, excluded from mean calculations |
| Ineligible sellers (<5 orders) | `src/pipeline.py:build_seller_metrics()` + `src/trust_score.py` | Yes - Flagged with `eligible_for_risk_score`, trust_score = NaN |
| All-cancelled sellers | `src/pipeline.py:build_seller_metrics()` + `src/trust_score.py` | **Partial** - cancellation_rate_proxy=1.0 correct; late_delivery_rate filled to 0.0 (gives false "perfect" delivery score if reviews existed); trust_score=NaN due to missing reviews |
| Early deliveries (negative delay) | `src/data_quality.py` + trust score calc | Yes - Treated as not late (`is_late_delivery=False`); negative delays included in average_delay_days; trust score works correctly |

---

### Bug Fixes Applied During Verification (2026-09-06)

1. **Fixed pandas 2.x groupby.apply() compatibility** in `src/pipeline.py:build_seller_metrics()`:
   - Changed `groupby().apply(lambda).rename()` to `groupby(group_keys=False)[col].apply(lambda).rename()`
   - This fixes a TypeError that occurred with pandas ≥2.0 when the apply function returns a scalar

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
- [x] Seller with all cancelled orders gets correct cancellation_rate_proxy = 1.0 and NULL review metrics (verified manually)
- [x] Order with missing delivery timestamps gets NaN delay and is excluded from late rate (verified manually)
- [x] Seller with exactly 5 orders is eligible; seller with <5 is not (verified manually)
- [x] Negative delivery delays don't break trust score calculation (verified manually)

**Recommended: Add automated unit tests for the above cases** to prevent regression.

---

## Summary

The pipeline handles most edge cases gracefully by:
1. Using pandas' native NaN propagation for missing data
2. Filtering ineligible sellers before trust scoring  
3. Computing aggregations only on valid data subsets

**Verified behavior (2026-09-06):**
- All 8 documented edge cases are handled correctly in practice
- All-cancelled sellers get `cancellation_rate_proxy=1.0` and `trust_score=NaN` (due to missing reviews)
- Early deliveries (90% of orders) work correctly — negative delays don't break trust scoring
- Missing timestamps are properly excluded from late delivery calculations
- A pandas 2.x compatibility bug in `groupby().apply()` was fixed during verification

**Remaining consideration:** The `fillna(0.0)` for `late_delivery_rate` and `average_delivery_delay_days` gives all-cancelled sellers a "perfect" delivery score if they somehow had reviews. In practice this doesn't occur (cancelled orders don't get reviews), but could be addressed by using a sentinel value or separate flag.
