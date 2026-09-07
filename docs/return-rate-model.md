# Next-Month Return Rate Model

**Issue:** #43 — Implement regression model for return rate prediction
**Run date:** 2026-09-07
**Reproduce:** `python scripts/train_return_rate_model.py --all-targets`

---

## The target is a proxy, and that matters

**Olist v1 has no returns data.** There is no column in any of the five raw CSVs recording a product
coming back. The project's established stand-in is `cancellation_rate_proxy` — the share of a
seller's orders reaching `order_status == "canceled"` — and that is what this model predicts.

This is stated first rather than in a footnote because the headline result depends on it. A model
described as "predicting return rate" that is actually predicting cancellations, on data where
cancellations are near-absent, would be misleading in a way that a reader could not detect from the
metrics alone.

## Framing

Take a seller's month *t* signals, predict that seller's month *t+1* rate. Three consequences:

1. **The unit is a seller-month, not a seller.** Collapsing a seller's whole history into one row
   discards the variation being predicted.
2. **The split is by time, not at random.** A random split trains on 2018 to predict 2017 — something
   no deployed model can do — and inflates the score.
3. **The baseline is persistence, not the mean.** "Next month looks like this month" is what an ops
   team would assume for free. Beating the global mean is trivial; beating persistence is the
   question worth asking.

**Panel:** 5,071 seller-months, 1,044 sellers, 21 months (2016-10 to 2018-08). Months with fewer than
5 orders are excluded — below that a single cancelled order moves the rate by 20 points or more.
3,358 of those rows have a genuine *consecutive* next month; a seller who trades in January and then
not until August does not get August treated as "next month".

**Split:** train 2,208 seller-months (2017-01 to 2018-02), test 1,149 (2018-03 to 2018-07).

**Features (month *t*):** cancellation rate, late delivery rate, negative review rate, average review
score, average delivery delay, order count, plus trailing three-month means of the first three.
Standardised on train statistics only.

**Model:** `sklearn.linear_model.LinearRegression`.

---

## Result 1 — the return rate proxy is not predictable

| | R² | MAE |
|---|---|---|
| **Model** | −0.0078 | 0.0050 |
| Baseline: persistence | −0.5283 | **0.0028** |
| Baseline: train mean | −0.0152 | 0.0052 |

**The model does not beat persistence, and the reason is in the data rather than the modelling.**

The target is **zero in 96.3% of seller-months**. Its mean is 0.0030 and its 95th percentile is still
exactly 0. The strongest available predictor — a seller's own trailing three-month cancellation rate
— correlates with next month's at **r = 0.072**. Month-over-month, this seller's own cancellation
rate is r = 0.057.

There is no month-to-month signal here to learn. Persistence wins on MAE by predicting zero and being
right 96% of the time; it loses badly on R² (−0.53) because when it is wrong it is wrong by the full
size of a spike. Neither is a good model. Adding features, adding trailing windows, or swapping in a
random forest cannot manufacture a signal that the data does not contain.

Reported as a finding rather than tuned around: **cancellations in Olist are rare, near-random events
at the seller-month level.** If this dashboard ever gets real returns data, re-run this script; the
machinery is ready and the answer may change.

## Result 2 — negative review rate is predictable, modestly

The same machinery pointed at a target the data actually supports. `--target
next_month_negative_review_rate`:

| | R² | MAE |
|---|---|---|
| **Model** | **+0.0131** | **0.0939** |
| Baseline: persistence | −0.7971 | 0.1168 |
| Baseline: train mean | −0.0498 | 0.0968 |

**The model beats both baselines.** It is 20% better than persistence on MAE (0.0939 vs 0.1168) and
it is the only one of the three with a positive R². That target is zero in 26.8% of seller-months
rather than 96.3%, and it autocorrelates at r = 0.215 — enough to learn from.

An R² of +0.013 is weak in absolute terms and should not be oversold: this explains roughly 1% of the
variance in next month's negative review rate. What it is good for is ranking, not point prediction —
which sellers are drifting the wrong way — and for that, beating persistence by 20% on MAE is a
usable improvement over the status quo of assuming next month resembles this one.

**Standardised coefficients** (comparable magnitudes, largest first):

| Feature | Coefficient |
|---|---|
| Trailing 3-month negative review rate | +0.0276 |
| Average review score | −0.0228 |
| Negative review rate (current month) | −0.0178 |
| Average delivery delay days | +0.0127 |
| Late delivery rate | +0.0094 |
| Trailing 3-month late delivery rate | −0.0084 |
| Total orders | +0.0044 |
| Cancellation rate | +0.0035 |
| Trailing 3-month cancellation rate | −0.0013 |

The trailing three-month rate outweighs the current month, and the current month's coefficient is
*negative* — the two together are doing mean-reversion: a month that spiked above the seller's recent
level tends to fall back. Delivery delay enters positively and independently, consistent with the
order-level threshold effect in [`docs/analytics-summary.md`](analytics-summary.md).

---

## What this does not do

- **No random forest or gradient boosting.** With the strongest linear signal at R² = 0.013, a
  higher-capacity model would fit noise and produce a better-looking training score for no real gain.
  If features with actual signal arrive, revisit.
- **No cross-validation folds.** A rolling-origin evaluation over multiple cutoffs would tighten the
  error bars. With 21 months and one clear finding per target, a single time-ordered split was enough
  to answer the question asked.
- **No calibration or prediction intervals.** Point estimates only.

## Files

| Path | Role |
|---|---|
| `src/return_rate_model.py` | Panel construction, time-split training, evaluation against both baselines |
| `scripts/train_return_rate_model.py` | CLI — `--target`, `--all-targets`, `--no-trailing` |
| `tests/test_return_rate_model.py` | 12 tests covering the order floor, consecutive-month targeting, cross-seller leakage, and scaler reuse |

## Reproduce

```bash
python scripts/run_pipeline.py --raw-dir data/raw --output-dir data/processed
python scripts/train_return_rate_model.py                 # the return rate proxy
python scripts/train_return_rate_model.py --all-targets   # every lagged rate side by side
```
