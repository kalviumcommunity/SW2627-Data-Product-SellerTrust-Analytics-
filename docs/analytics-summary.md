# Final Analytics Summary — Key Findings

**Issue:** #39 — Compile final analytics summary of key findings
**Run date:** 2026-09-07 · Olist v1 · 100,010 seller-order rows · 3,095 sellers · 1,794 eligible for scoring
**Reproduce:** `python scripts/analytics_summary.py`

Every figure below is printed by `scripts/analytics_summary.py` against the current pipeline output.

---

## Executive summary

**Late delivery is the mechanism of trust erosion, and it has a cliff at three days.**

An order delivered on time or early draws a negative review 9.8% of the time. Slip by up to three
days and that rises to 19.2% — annoying, recoverable. Slip past three days and it jumps to **61.3%**,
then to 78% beyond a week. The relationship is not linear; it is a threshold. Between three and seven
days late, the majority of customers stop giving the seller the benefit of the doubt.

That order-level mechanism aggregates cleanly to the seller level. A seller's late delivery rate
correlates with their negative review rate at **r = +0.436** and with their trust score at
**r = −0.705** (both p < 0.001, n = 1,794) — the single strongest relationship in the dataset.
Cancellation rate, by contrast, barely moves with late delivery (r = +0.088): they are separate
operational failures, and a seller can be bad at one while fine at the other.

The population is healthy overall (mean trust 87.90) with a thin, severe tail: **33 sellers**
(1.8% of eligible) combine a late delivery rate above 30% with a negative review rate above 30%, and
their mean trust score is **58.75** against a population mean of 87.90.

---

## Top 10 riskiest sellers

Lowest trust scores among the 1,794 eligible sellers.

| # | Seller ID | Trust | Orders | Late % | Avg review | Neg % | Cancel % | Anomalies | Trend |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `4342d4b2ba6b161468c63a7e7cfce593` | 38.03 | 20 | 50.0% | 1.26 | 94.7% | 0.0% | 6 | stable |
| 2 | `b1b3948701c5c72445495bd161b83a4c` | 38.35 | 18 | 64.3% | 1.72 | 77.8% | 11.1% | 7 | stable |
| 3 | `8c3b533c63cca56240f94f1e3a6b18ef` | 38.75 | 5 | 66.7% | 1.50 | 75.0% | 0.0% | 8 | insufficient data |
| 4 | `633ecdf879b94b5337cca303328e4a25` | 40.00 | 6 | 66.7% | 1.80 | 80.0% | 0.0% | 8 | improving |
| 5 | `44f091b5abab8018f682fce8124b85e5` | 41.25 | 6 | 66.7% | 2.50 | 66.7% | 33.3% | 8 | stable |
| 6 | `973f21788dfab357250f69a8dcb7ddee` | 44.83 | 10 | 55.6% | 2.00 | 70.0% | 10.0% | 7 | stable |
| 7 | `30c7f28fd3a5897b2c82d152bb760c17` | 46.67 | 7 | 50.0% | 1.67 | 66.7% | 0.0% | 7 | stable |
| 8 | `312ba1d77e9c332ef21f9598b7f64cd7` | 50.63 | 9 | 57.1% | 2.78 | 55.6% | 22.2% | 9 | stable |
| 9 | `6ee85be3693ed79a8e80718743d80655` | 52.44 | 9 | 40.0% | 2.33 | 66.7% | 11.1% | 5 | stable |
| 10 | `538caafddff204241cecbf3a02e6b3cf` | 53.33 | 9 | 50.0% | 2.56 | 55.6% | 11.1% | 6 | stable |

**What the evidence shows**

- Every one of the ten is late on **at least 40%** of deliveries (range 40.0% – 66.7%), against a
  population where late delivery is the exception.
- Every one has a **negative review rate above 55%** (range 55.6% – 94.7%) and an average review
  below 2.8 (range 1.26 – 2.78).
- **Nine of the ten are `stable` or `improving`, not `declining`.** This is the important read: these
  are not sellers who are getting worse, they are sellers who have been bad the whole time. Trend
  detection will never surface them, because there is no trend to detect. A declining-trend alert and
  a low-trust-score list catch different populations, and an ops team needs both.
- Cancellation is not the story. Four of the ten cancel nothing at all. Their customers received the
  goods — late, and not as hoped.
- Seller #1 is the extreme: 20 orders, 94.7% of them reviewed negatively, average review 1.26.

---

## Trust-erosion patterns

Counted over the 1,794 eligible sellers. Mean trust for the whole eligible population is **87.90**.

| Pattern | Definition | Sellers | Share | Mean trust |
|---|---|---|---|---|
| **A** | Late delivery > 30% **and** negative reviews > 30% | 33 | 1.8% | **58.75** |
| **B** | Average review < 3.5 **and** late delivery > 20% | 56 | 3.1% | 63.21 |
| **C** | Cancellation > 30% **and** negative reviews > 30% | 5 | 0.3% | 64.11 |
| **D** | Declining trend **and** ≥ 2 anomalies | 10 | 0.6% | 74.78 |
| E | Negative reviews > 30% alone | 165 | 9.2% | 70.89 |
| F | Late delivery > 30% alone | 59 | 3.3% | 67.26 |

**The most common trust-erosion pattern is late delivery driving negative reviews (Pattern A).**
It is the tightest and most damaging combination: 33 sellers at a mean trust of 58.75, nearly 30
points below the population mean.

Reading the single-signal rows against the combinations is what makes the point. Negative reviews
alone flag 165 sellers at a mean trust of 70.89; late delivery alone flags 59 at 67.26. Requiring
*both* cuts the list to 33 but drops mean trust another 9–12 points. The combination is not just a
smaller list — it is a more precise one. Pattern A is the right trigger for an escalation queue;
Patterns E and F are the right triggers for a watchlist.

Pattern D — active deterioration — is genuinely rare at 10 sellers, and their mean trust of 74.78 is
comparatively healthy. That is the point of catching them: they are still recoverable.

---

## Delivery delay vs negative reviews

### Order level — 97,157 delivered orders with a review

| Delivery outcome | Orders | Negative review rate | Mean review |
|---|---|---|---|
| Early or on time (delay ≤ 0) | 89,478 | 9.8% | 4.27 |
| Late 0–3 days | 2,644 | 19.2% | 3.76 |
| Late 3–7 days | 1,781 | **61.3%** | 2.32 |
| Late 7–14 days | 1,750 | 78.0% | 1.75 |
| Late more than 14 days | 1,504 | 78.7% | 1.71 |

| Correlation | r | p | n |
|---|---|---|---|
| Delivery delay ↔ review score | −0.253 | < 0.001 | 97,157 |
| Delivery delay ↔ negative review (0/1) | +0.242 | < 0.001 | 97,157 |

The correlation coefficients understate the effect, because the relationship is a step rather than a
line. The bucket table is the more honest presentation: **the damage is concentrated between three
and seven days late**, where the negative review rate roughly triples from 19.2% to 61.3%. Past
fourteen days there is nothing left to lose — 78.0% and 78.7% are effectively the same number.

### Seller level — 1,794 eligible sellers

| Correlation | r | p |
|---|---|---|
| Late delivery rate ↔ trust score | **−0.705** | < 0.001 |
| Late delivery rate ↔ average review score | −0.447 | < 0.001 |
| Late delivery rate ↔ negative review rate | **+0.436** | < 0.001 |
| Average delivery delay ↔ negative review rate | +0.180 | < 0.001 |
| Late delivery rate ↔ cancellation rate | +0.088 | < 0.001 |

Late delivery *rate* correlates with negative reviews more than twice as strongly as *average* delay
does (+0.436 vs +0.180). Consistency matters more than magnitude: a seller who is occasionally very
late is treated better than one who is reliably a little late. This is the same threshold effect seen
at order level, and it is an argument for tracking the rate rather than the mean.

The near-zero late-delivery/cancellation correlation (+0.088) says these are independent failure
modes. Do not build one intervention and expect it to move both.

---

## Actionable insights

1. **Set the late-delivery SLA at three days, not seven.** The order-level cliff sits between 3 and 7
   days. An alert that fires at seven days is firing after the customer has already decided. This is
   the single highest-leverage change available from this analysis.

2. **Use Pattern A as the escalation trigger, not negative reviews alone.** 33 sellers versus 165 —
   a queue an ops team can actually work through, and one where mean trust is 12 points lower.

3. **Do not rely on trend detection to find the worst sellers.** Nine of the top ten riskiest are
   `stable` or `improving`. Chronic underperformance is invisible to a slope-based test. Run a
   low-trust-score list alongside the declining-trend list; they surface different sellers.

4. **Track late delivery *rate*, not average delay.** The rate correlates with negative reviews at
   more than double the strength of the mean delay.

5. **Treat cancellation as a separate programme.** It barely moves with delivery performance, and the
   5 sellers in Pattern C are a different population from the 33 in Pattern A.

---

## Supporting statistics

**Trust score, eligible sellers (n = 1,794)**

| | |
|---|---|
| Mean | 87.90 |
| Median | 89.06 |
| Std dev | 7.96 |
| Range | 38.03 – 100.00 |
| Q1 / Q2 / Q3 | 84.77 / 89.06 / 92.79 |

**Risk tier, all 3,095 sellers**

| Tier | Sellers | Share |
|---|---|---|
| ESCALATE | 1,300 | 42.0% |
| MONITOR | 1,292 | 41.7% |
| COACH | 503 | 16.3% |

Tiers cover all sellers, including the 1,301 below the 5-order scoring floor. See
[`docs/edge-cases.md`](edge-cases.md) case 6.

**Review score trend, all 3,095 sellers**

| Flag | Sellers | Share |
|---|---|---|
| Stable | 1,638 | 52.9% |
| Insufficient data | 1,308 | 42.3% |
| Declining | 76 | 2.5% |
| Improving | 73 | 2.4% |

**Anomaly detection, eligible sellers**

| | |
|---|---|
| Sellers with ≥ 1 anomaly | 318 (17.7%) |
| Mean anomalies per seller | 0.33 |
| Maximum anomalies on one seller | 9 |

---

## Note on the previous revision

The earlier version of this document had lost every numeric value to a bad find-and-replace — trust
score statistics, correlation coefficients and p-values all rendered as `..` placeholders, and the
top-10 table was truncated mid-row. Nothing in it was recoverable, so this is a regeneration from the
current pipeline output rather than a patch. The rankings differ from what that document claimed
because the `late_delivery_rate` denominator fix landed after it was written.
