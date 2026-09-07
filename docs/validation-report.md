# End-to-End Data Validation Report

**Issue:** #36 — Run end-to-end data validation from raw to final
**Run date:** 2026-09-07 · Python 3.11.15 · pandas 2.3.3
**Reproduce:** `python scripts/validate_pipeline.py`

The pipeline was run from a cleared `data/processed/` against the five raw Olist v1 CSVs. Every
figure below is printed by `scripts/validate_pipeline.py`; nothing here is hand-entered.

**Result: PASSED — 14 of 14 checks green.**

---

## Row counts at each stage

| Stage | Rows |
|---|---|
| Raw orders (`olist_orders_dataset.csv`) | 99,441 |
| Raw order items (`olist_order_items_dataset.csv`) | 112,650 |
| Raw reviews (`olist_order_reviews_dataset.csv`) | 99,224 |
| Raw sellers (`olist_sellers_dataset.csv`) | 3,095 |
| Seller-order fact rows | 100,010 |
| — distinct orders within the fact table | 98,666 |
| Seller metrics rows | 3,095 |

Two of these deserve a note, because the numbers look wrong until you know why:

- **99,441 orders become 98,666.** 775 orders have no line item and therefore no seller, so they
  cannot be attributed and do not enter the fact table. They are almost all orders that never
  reached fulfilment (603 `unavailable`, 164 `canceled`).
- **98,666 orders become 100,010 rows.** 1,278 orders were fulfilled by more than one seller, and
  each seller gets its own row so that one order is not double-counted against either of them.

## Coverage checks

| Check | Result |
|---|---|
| Every seller with at least one item is scored | PASS — 3,095 metric rows vs 3,095 sellers in the items table |
| No duplicate seller rows | PASS — 3,095 distinct ids |
| Fact table covers every order that has line items | PASS — 98,666 of 98,666 |
| Every seller has a risk tier | PASS |

All **3,095** sellers are processed and tiered. That is the full seller population in the dataset.

## Trust score coverage

| | Sellers | Share |
|---|---|---|
| Eligible (≥ 5 orders) | 1,794 | 58.0% |
| Ineligible (< 5 orders) | 1,301 | 42.0% |

| Check | Result |
|---|---|
| Eligibility flag matches the ≥ 5 order threshold | PASS |
| No eligible seller is missing a trust score | PASS — 0 nulls |
| Every ineligible seller has a null trust score | PASS — 0 unexpected scores |
| Trust scores lie within 0–100 | PASS |

**Trust score distribution (eligible sellers, n = 1,794)**

| | |
|---|---|
| Mean | 87.90 |
| Median | 89.06 |
| Std dev | 7.96 |
| Range | 38.03 – 100.00 |

The 1,301 nulls in `trust_score` are the ineligible sellers and are the intended state, not a
defect: fewer than five orders is too thin a base for a stable score. See
[`docs/edge-cases.md`](edge-cases.md) case 6.

## Value range checks

| Column | Observed range | Result |
|---|---|---|
| `late_delivery_rate` | 0.0000 – 1.0000 | PASS (within 0–1) |
| `negative_review_rate` | 0.0000 – 1.0000 | PASS (within 0–1) |
| `cancellation_rate_proxy` | 0.0000 – 1.0000 | PASS (within 0–1) |
| `average_review_score` | 1.00 – 5.00 | PASS (within 1–5) |
| `total_orders` | all > 0 | PASS |
| `cancelled_orders` | never exceeds `total_orders` | PASS |

## Nulls per column

| Column | Nulls | Expected? |
|---|---|---|
| `seller_id` | 0 | — |
| `total_orders` | 0 | — |
| `cancelled_orders` | 0 | — |
| `average_review_score` | 5 | Yes — 5 sellers have no reviews at all |
| `negative_review_rate` | 0 | — |
| `average_response_time_hours` | 5 | Yes — same 5 review-less sellers |
| `late_delivery_rate` | 0 | — |
| `average_delivery_delay_days` | 0 | — |
| `cancellation_rate_proxy` | 0 | — |
| `eligible_for_risk_score` | 0 | — |
| `trust_score` | 1,301 | Yes — ineligible sellers, by design |
| `risk_tier` | 0 | — |

Every null in the output is accounted for. None are silent failures.

## Risk tier distribution

| Tier | Sellers | Share |
|---|---|---|
| ESCALATE | 1,300 | 42.0% |
| MONITOR | 1,292 | 41.7% |
| COACH | 503 | 16.3% |

Tiers are assigned to all 3,095 sellers, including the ineligible ones — a 100% cancellation rate on
two orders is worth surfacing even when the sample is too small to score. Treat an ineligible
seller's tier as a triage hint rather than a measurement.

## Downstream stages

Both stages run cleanly on the validated outputs.

**Trend detection** (`python scripts/detect_trends.py`) — 3,090 sellers.

| Flag | Sellers |
|---|---|
| Declining | 76 |
| Improving | 73 |
| Stable | 1,638 |
| Insufficient data | 1,303 |

The 5 sellers missing from the 3,095 are the review-less ones: with no review history there is
nothing to regress.

**Anomaly detection** (`python scripts/detect_anomalies.py`) — 1,794 sellers scored (eligible only).

| | |
|---|---|
| Sellers with at least one anomaly | 318 (17.7% of eligible) |
| Mean anomalies per seller | 0.33 |

---

## Changes from the previous revision of this report

The earlier version of this file was written before the `late_delivery_rate` denominator fix landed
and was never refreshed, so several of its figures no longer matched a live run:

| Figure | Previously reported | Actual |
|---|---|---|
| Raw orders | 100,010 | 99,441 — 100,010 is the *fact row* count, not the raw order count |
| Trust score mean | 88.01 | 87.90 |
| Trust score std dev | 7.68 | 7.96 |
| Trust score minimum | 40.00 | 38.03 |
| Sellers with any anomaly | 780 of 3,095 (25.2%) | 318 of 1,794 eligible (17.7%) |

The trust score figures moved when `late_delivery_rate` switched to using delivered orders with
valid dates as its denominator (see [`docs/cross-validation-report.md`](cross-validation-report.md)).
The anomaly figure moved when `scripts/detect_anomalies.py` was corrected in #79 to match the
function signature it calls, which also narrowed the population to eligible sellers.

To stop this drift recurring, the figures now come from `scripts/validate_pipeline.py` rather than
from an ad-hoc session, and the script exits non-zero when a check fails so it can be wired into CI
or a release gate.
