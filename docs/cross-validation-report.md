# Cross-Validation Report: Dashboard Outputs vs Raw Data

**Issue:** #28 — Cross-validate dashboard outputs against raw data
**Run date:** 2026-09-07
**Reproduce:** `python scripts/spot_check_sellers.py` (seeded, so the sample is stable)

Ten sellers were sampled across risk tiers and re-measured directly from the raw Olist CSVs by
`scripts/spot_check_sellers.py`, which reimplements each metric independently and never imports
`src/`. If the pipeline and the reference disagree, one of them is wrong.

**Result: 60 of 60 metric comparisons match**, after the one real discrepancy this check found was
fixed in #85.

---

## Sample

Two sellers from each risk tier, plus the lowest trust scores and the highest order volumes — a
metric bug does the most damage at the extremes, so the sample is anchored there rather than being
purely random.

| # | Seller | Tier | Orders | Delivered | Reviews |
|---|---|---|---|---|---|
| 1 | `6a8b085f816a1f75f92dbac6eb545f8f` | COACH | 127 | 125 | 128 on 127 orders |
| 2 | `bba74270a87732727b5a3b4fd9ac1c39` | COACH | 36 | 35 | 36 |
| 3 | `ab3e0c171fe84a7ba7de130f19cfb485` | ESCALATE | 7 | 6 | 7 |
| 4 | `3febca52652e7209509ccfe61cbde40e` | ESCALATE | 2 | **0** | 2 |
| 5 | `5a9b3bcab695173c820e53934574ae80` | MONITOR | 1 | 1 | 1 |
| 6 | `5de1c80811ce7007f62f00d971236c09` | MONITOR | 2 | 2 | 2 |
| 7 | `4342d4b2ba6b161468c63a7e7cfce593` | ESCALATE | 20 | 2 | 19 |
| 8 | `b1b3948701c5c72445495bd161b83a4c` | ESCALATE | 18 | 14 | 18 |
| 9 | `6560211a19b47992c3666cc44a7e94c0` | COACH | 1,854 | 1,819 | 1,844 on 1,838 orders |
| 10 | `4a3ca9315b744ce9f8e9374361493884` | ESCALATE | 1,806 | 1,772 | 1,801 on 1,785 orders |

Six metrics are checked per seller: `total_orders`, `cancelled_orders`, `late_delivery_rate`,
`average_delivery_delay_days`, `average_review_score`, `negative_review_rate`.

## Results

| Metric | Matches | Notes |
|---|---|---|
| `total_orders` | 10/10 | Exact, including the two ~1,800-order sellers |
| `cancelled_orders` | 10/10 | Exact |
| `late_delivery_rate` | 10/10 | Exact to 0.0001 |
| `average_delivery_delay_days` | 10/10 | 9/10 before #85 — see below |
| `average_review_score` | 10/10 | Exact to 0.0001 |
| `negative_review_rate` | 10/10 | Exact to 0.0001 |

## Discrepancy found, and fixed

**Seller `3febca52652e7209509ccfe61cbde40e` — `average_delivery_delay_days`: dashboard reports
`0.0`, raw data says "unknown".**

Both of this seller's orders were cancelled, so nothing was ever delivered and there is no delay to
average. The pipeline's `fillna(0.0)` turned that absence into a confident zero, which reads as "this
seller delivers exactly on the estimated date" — the single most average-looking value it could have
picked. 125 sellers in the dataset are in this position.

This was a real data integrity issue, not a tolerance artefact. It was fixed in
[#85](https://github.com/kalviumcommunity/SW2627-Data-Product-SellerTrust-Analytics-/pull/85):
`average_delivery_delay_days` is left `NaN` when there is no delivery to measure, and a new
`delivered_orders_with_dates` column exposes the denominator behind both delivery metrics. With that
merged, this check now reports **60/60 and exits 0**.

Worth noting how it surfaced: the mismatch was found by an independent reimplementation disagreeing
with the pipeline, not by anyone reading the pipeline code. That is the argument for keeping this
script around rather than treating cross-validation as a one-off exercise.

## Two ways to get the reference wrong

Both of these were hit while writing the check, and both produce a mismatch that looks exactly like a
pipeline bug. They are recorded here so the next person does not spend the afternoon on them.

### Delivery delay must be computed in fractional days

Using `Series.dt.days` on the delivered-minus-estimated timedelta floors towards negative infinity:
an order delivered 8.2 days early becomes 9 days early, and an order 3 hours late becomes on time.
Averaged over a seller, the reference then sits **0.6 to 0.85 days below** the pipeline for every
single seller — consistent, directional, and utterly convincing as a pipeline bug. It is not one.

| Seller | Reference with `.dt.days` | Reference with fractional days | Pipeline |
|---|---|---|---|
| `3db66a856d18a9cba7c9241fc5221c50` | −11.84 | −11.12 | −11.12 |
| `289cdb325fb7e7f891c38608bf9e0962` | −10.38 | −9.66 | −9.66 |

The truncation also changes the *late rate*, because an order 3 hours past estimate is late in
fractional days and on time in floored days: 0.1064 vs 0.1170 for the first seller above. The
pipeline's fractional-day treatment is correct.

### Review scores are averaged per order, not per review row

547 of 98,673 orders carry more than one review. The pipeline collapses those to a per-order mean
before aggregating to the seller, so one disputed order cannot outvote the rest. Averaging raw review
rows instead shifts a seller's score by up to ~0.015 and the negative review rate by up to ~0.007:

| Seller | Per order (pipeline) | Per review row |
|---|---|---|
| `6a8b085f816a1f75f92dbac6eb545f8f` | 4.1220 | 4.1094 |
| `6560211a19b47992c3666cc44a7e94c0` | 3.9358 | 3.9371 |

"One order, one voice" is the right convention, so the reference implementation adopts it and prints
the row-level alternative alongside whenever a sampled seller has a doubly-reviewed order.

## Previously fixed

The `late_delivery_rate` denominator was corrected in earlier work on this issue: it now divides by
delivered orders that have valid dates, rather than by all orders including cancelled and in-flight
ones. Before that fix 476 of 3,095 sellers (15.4%) disagreed with the raw data; after it, zero do.
All ten sellers in this sample match exactly.

## How to re-run

```bash
python scripts/run_pipeline.py --raw-dir data/raw --output-dir data/processed
python scripts/spot_check_sellers.py                     # 10 sellers, seed 28
python scripts/spot_check_sellers.py --sample-size 25 --seed 7   # a different sample
```

The script exits non-zero when a metric mismatches, so it can gate a release alongside
`scripts/validate_pipeline.py`.
