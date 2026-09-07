# Edge Cases in Data Processing

**Issue:** #31 — Document edge cases in data processing
**Dataset:** Olist v1 (`data/raw/`, 5 CSVs) · 100,010 seller-order rows · 3,095 sellers
**Code reviewed:** `src/pipeline.py`, `src/data_quality.py`, `src/trust_score.py`, `src/risk_tier.py`, `src/anomaly_detection.py`

Every count below was measured against the current pipeline output, not estimated. Reproduce with
`python scripts/run_pipeline.py --raw-dir data/raw --output-dir data/processed`.

---

## Summary

| # | Edge case | Sellers / rows affected | Status |
|---|---|---|---|
| 1 | Seller with zero reviews | 5 sellers | **Fixed** — metric left `NaN`, no longer imputed |
| 2 | Seller with all orders cancelled | 39 sellers | Handled — escalates on cancellation rate |
| 3 | Order missing a delivery timestamp | 2,193 rows | Handled — excluded from delivery metrics |
| 4 | Seller with no completed delivery at all | 125 sellers | **Fixed** — delay left `NaN`, denominator exposed |
| 5 | Order marked `delivered` but with no delivery date | 8 rows | Handled — excluded, status left untouched |
| 6 | Seller below the 5-order eligibility floor | 1,301 sellers | Handled — `trust_score` is `NA` by design |
| 7 | Multi-seller (split) order | 1,278 orders / 1,344 extra rows | Handled — grouped by order **and** seller |
| 8 | Impossible timeline (delivery before purchase) | 0 rows in v1 | Handled — pipeline fails fast |
| 9 | Non-numeric / out-of-range review score | 0 rows in v1 | Handled — coerced to `NA`, clipped on scoring |
| 10 | Order with no line items | 775 orders | Handled — dropped, cannot be attributed to a seller |

---

## 1. Seller with zero reviews — 5 sellers

Five sellers have orders but not a single review row. All five have exactly one order, so none of
them are eligible for a trust score.

**Previous handling (wrong).** `build_seller_metrics()` imputed a neutral `3.0` average review score
and a `0.0` negative review rate. Both are fabrications: 3.0 is not what these sellers scored, it is
what we assumed. Worse, 3.0 sits below the `escalate` review threshold of 3.5 in
`src/config/thresholds.yaml`, so the imputed value pushed sellers into `ESCALATE` on evidence that
did not exist.

**Current handling.** Both metrics stay `NaN`:

```python
average_review_score=("review_score", "mean"),
negative_review_rate=("review_score", lambda s: s.dropna().le(2).mean() if s.notna().any() else np.nan),
```

`assign_risk_tier()` in `src/risk_tier.py` already guards every comparison with `pd.isna()`, so a
`NaN` reads as "this threshold was not met" rather than as a breach. One of the five sellers moved
from `ESCALATE` to `MONITOR` as a result; the other four still escalate, but now on real
cancellation and late-delivery evidence rather than on an imputed review score.

## 2. Seller with all orders cancelled — 39 sellers

34 have one order, 4 have two, 1 has three. Every one of them lands at
`cancellation_rate_proxy = 1.0`, far above the 2.5% escalate threshold, so all 39 are correctly
flagged `ESCALATE`. None reach the 5-order floor, so none receive a trust score — the tier is the
signal, not the score.

No code change needed. Note that a cancelled order still contributes to `total_orders`; that is
deliberate, since the denominator is "orders taken", not "orders fulfilled".

## 3. Order missing a delivery timestamp — 2,193 rows

`order_delivered_customer_date` is null on 2,193 of 100,010 rows. `order_estimated_delivery_date` is
never null in v1.

| `order_status` | rows |
|---|---|
| shipped | 1,108 |
| canceled | 455 |
| invoiced | 312 |
| processing | 301 |
| delivered | 8 |
| unavailable | 7 |
| approved | 2 |

`parse_order_datetimes()` in `src/data_quality.py` coerces unparseable dates to `NaT` instead of
raising, and `build_seller_metrics()` restricts the delivery denominator to rows that are both
`order_status == "delivered"` and have the two dates present. An in-flight order therefore neither
counts as late nor as on time — it simply does not vote.

## 4. Seller with no completed delivery at all — 125 sellers

93 have one order, 27 have two, 4 have three, and one has seven. This is the case that matters most,
because it is invisible: a seller with nothing delivered and a seller with a spotless 94-delivery
record both used to report `late_delivery_rate = 0.0` and `average_delivery_delay_days = 0.0`.

**Current handling.** `build_seller_metrics()` now emits a `delivered_orders_with_dates` column
carrying the denominator behind both delivery metrics, and leaves the descriptive
`average_delivery_delay_days` as `NaN` when that denominator is zero:

```python
delivered_counts = by_seller.size().rename("delivered_orders_with_dates")
...
metrics["late_delivery_rate"] = metrics["late_delivery_rate"].fillna(0.0)
```

`late_delivery_rate` deliberately stays `0.0` rather than becoming `NaN`, because
`src/trust_score.py` multiplies `(1 - late_delivery_rate)`; a `NaN` there would null out the trust
score of the one eligible seller in this group. `delivered_orders_with_dates == 0` is the flag that
tells a consumer the rate is uninformed. Exactly one of the 125 sellers is eligible for scoring.

## 5. Order marked `delivered` with no delivery date — 8 rows

A status/timestamp contradiction in the source data. These 8 rows are excluded from the delivery
denominator by the same filter as case 3. The pipeline does not rewrite `order_status`, because the
raw status is the record of what the marketplace believed; the missing timestamp is the anomaly, and
silently reclassifying the order would hide it.

## 6. Seller below the 5-order eligibility floor — 1,301 sellers (42.0%)

`build_seller_metrics()` sets `eligible_for_risk_score = total_orders >= 5`, and
`src/trust_score.py` sets `trust_score` to `pd.NA` for everyone below the floor. This is why
`trust_score` has 1,301 nulls, and that is the intended state, not a data quality failure.

Ineligible sellers still receive a `risk_tier`, because a 100% cancellation rate on two orders is
still worth surfacing. Read those tiers as a triage hint on thin evidence, not as a score.

## 7. Multi-seller (split) order — 1,278 orders, 1,344 extra rows

98,666 orders with line items expand to 100,010 seller-order rows, because an order fulfilled by two
sellers is two rows; 1,278 orders involve more than one seller. `build_seller_order_fact()` groups
items by **both** `order_id` and `seller_id` before merging, and the merges use `validate="m:1"` so
an unexpected fan-out raises instead of silently duplicating one order across sellers.

Consequence worth knowing: `total_orders` uses `nunique()` on `order_id` within a seller, while the
delivery denominator counts seller-order rows. For a single seller the two agree, since a seller
appears at most once per order.

## 8. Impossible timeline — 0 rows in v1

`validate_order_timeline()` in `src/data_quality.py` checks four relations: approval after purchase,
carrier handoff after purchase, delivery after purchase, and delivery after carrier handoff.
`require_valid_orders()` raises a `ValueError` naming the failing check and row count. Olist v1
passes all four cleanly, so this path is a guard for future data rather than a live fix.

## 9. Non-numeric or out-of-range review score — 0 rows in v1

`pd.to_numeric(..., errors="coerce").astype("Int64")` turns any unparseable review score into `<NA>`
rather than raising, and `_normalise_0_100()` in `src/trust_score.py` clips before scaling, so a
hypothetical score of 7 cannot push a component above 100. No v1 rows exercise either guard.

## 10. Order with no line items — 775 orders

`olist_orders_dataset.csv` holds 99,441 orders, but `olist_order_items_dataset.csv` only references
98,666 of them. The remaining 775 have no line item and therefore no seller.
`build_seller_order_fact()` builds outward from the items table and left-joins orders onto it, so an
order with no item never enters the fact table at all. That is the only correct outcome — an order that cannot be
attributed to a seller cannot contribute to any seller's metrics — but it is worth stating, because
it is why the row count moves from 99,441 to 100,010 rather than to something larger.

They are overwhelmingly orders that never reached fulfilment: 603 `unavailable`, 164 `canceled`,
5 `created`, 2 `invoiced`, 1 `shipped`.

---

## Division-by-zero audit

| Site | Denominator | Guard |
|---|---|---|
| `late_delivery_rate` | delivered rows with dates | `groupby().mean()` yields no row for an empty group; the subsequent `fillna(0.0)` supplies the value |
| `average_delivery_delay_days` | same | left `NaN` (case 4) |
| `cancellation_rate_proxy` | `total_orders` | a seller only exists in the frame because it has at least one order |
| `negative_review_rate` | non-null reviews | explicit `if s.notna().any()` branch (case 1) |
| `detect_iqr_outliers` / `detect_zscore_anomalies` | IQR / std dev | both return all-`False` when the spread is zero |

## Known gaps

- `average_response_time_hours` is `NaN` for the same 5 review-less sellers. It is descriptive only
  and feeds no threshold, so it is left alone.
- Ineligible sellers are tiered on as little as one order. Splitting `risk_tier` into a separate
  `INSUFFICIENT_DATA` value would be more honest, but it changes a column the Streamlit filters read
  and belongs in its own issue rather than here.
