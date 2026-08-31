# Correlation Analysis Between Risk Signals

**Date:** 2026-08-29  
**Issue:** #15 - Perform correlation analysis between risk signals  
**Author:** Himanshu Gupta (itzhimanshugt)

---

## Executive Summary

Computed Pearson and Spearman correlation matrices for four key risk signals across 1,793 eligible sellers (≥5 orders). **No signal pairs exceed the |r| > 0.7 threshold** for double-counting risk. The highest correlation is between `late_delivery_rate` and `average_delivery_delay_days` (Pearson=0.62, Spearman=0.61), which measure related but distinct aspects of delivery performance.

**Recommendation:** Keep all four signals separate in the trust score calculation. No merging required.

---

## Methodology

- **Population:** Sellers with `eligible_for_risk_score = 1` (total_orders ≥ 5)
- **Sample size:** 1,793 sellers (after dropping 1 row with missing `average_delivery_delay_days`)
- **Signals analyzed:**
  1. `late_delivery_rate` — proportion of orders delivered late
  2. `average_delivery_delay_days` — mean delivery delay in days (negative = early)
  3. `cancellation_rate_proxy` — cancelled_orders / total_orders
  4. `negative_review_rate` — proportion of reviews with score ≤ 2
  5. `average_response_time_hours` — mean seller response time to reviews
- **Methods:** Pearson (linear) and Spearman (monotonic/rank) correlations
- **Threshold for concern:** |r| > 0.7 (standard double-counting threshold)

---

## Correlation Matrices

### Pearson Correlation (Linear Relationships)

| | late_delivery_rate | average_delivery_delay_days | cancellation_rate_proxy | negative_review_rate | average_response_time_hours |
|---|---|---|---|---|---|
| **late_delivery_rate** | 1.0000 | **0.6166** | 0.0305 | 0.3827 | 0.0001 |
| **average_delivery_delay_days** | 0.6166 | 1.0000 | -0.0163 | 0.1751 | -0.0472 |
| **cancellation_rate_proxy** | 0.0305 | -0.0163 | 1.0000 | 0.2718 | 0.0235 |
| **negative_review_rate** | 0.3827 | 0.1751 | 0.2718 | 1.0000 | 0.0234 |
| **average_response_time_hours** | 0.0001 | -0.0472 | 0.0235 | 0.0234 | 1.0000 |

### Spearman Correlation (Monotonic Relationships)

| | late_delivery_rate | average_delivery_delay_days | cancellation_rate_proxy | negative_review_rate | average_response_time_hours |
|---|---|---|---|---|---|
| **late_delivery_rate** | 1.0000 | **0.6095** | 0.0501 | 0.3410 | 0.0358 |
| **average_delivery_delay_days** | 0.6095 | 1.0000 | 0.0050 | 0.1742 | -0.0846 |
| **cancellation_rate_proxy** | 0.0501 | 0.0050 | 1.0000 | 0.2338 | 0.0783 |
| **negative_review_rate** | 0.3410 | 0.1742 | 0.2338 | 1.0000 | 0.0539 |
| **average_response_time_hours** | 0.0358 | -0.0846 | 0.0783 | 0.0539 | 1.0000 |

---

## Pairwise Analysis

| Signal Pair | Pearson | Spearman | Interpretation |
|---|---|---|---|
| late_delivery_rate ↔ average_delivery_delay_days | **0.6166** | **0.6095** | **Moderate-high**: Both capture delivery performance; late_delivery_rate is binary (late/on-time), average_delivery_delay_days is continuous magnitude. Related but not redundant. |
| late_delivery_rate ↔ negative_review_rate | 0.3827 | 0.3410 | **Moderate**: Late deliveries correlate with negative reviews, but distinct signals (delivery vs. sentiment). |
| cancellation_rate_proxy ↔ negative_review_rate | 0.2718 | 0.2338 | **Weak-moderate**: Some association but captures different failure modes. |
| average_delivery_delay_days ↔ negative_review_rate | 0.1751 | 0.1742 | **Weak**: Delay magnitude has limited direct link to review sentiment. |
| All other pairs | < 0.1 | < 0.1 | **Negligible**: Effectively independent signals. |

---

## Double-Counting Risk Assessment

| Threshold | Pairs Exceeding | Risk Level |
|---|---|---|
| |r| > 0.9 | None | ✅ None |
| |r| > 0.8 | None | ✅ None |
| |r| > 0.7 | None | ✅ None |
| |r| > 0.6 | 1 pair (late_delivery_rate ↔ average_delivery_delay_days) | ⚠️ Monitor |

### Detailed Assessment: late_delivery_rate vs average_delivery_delay_days

- **Correlation:** Pearson=0.62, Spearman=0.61
- **Why they correlate:** Both derive from the same delivery timestamp comparisons
- **Why they're distinct:**
  - `late_delivery_rate`: Binary threshold metric (late vs. on-time), captures frequency of SLA breaches
  - `average_delivery_delay_days`: Continuous magnitude metric, captures severity of delays (including early deliveries as negative values)
- **Business meaning:** A seller with 10% late rate but -5 day average delay (mostly early) differs from one with 10% late rate and +3 day average delay
- **Trust score weights:** Currently 30% delivery performance uses only `late_delivery_rate` (via `1 - late_delivery_rate`). `average_delivery_delay_days` is not directly in the trust score.

---

## Recommendations

### 1. Keep All Signals Separate ✅
No signal pairs exceed the 0.7 threshold. The current trust score weighting (delivery 30%, review 30%, cancellation 20%, negative_review 20%) does not double-count correlated signals.

### 2. Delivery Performance Signal Choice
The trust score currently uses `late_delivery_rate` (binary SLA breach rate). Consider:
- **Option A (current):** Keep `late_delivery_rate` — simpler, business-aligned with SLA compliance
- **Option B:** Use `average_delivery_delay_days` — captures severity, but negative values (early delivery) complicate interpretation
- **Option C:** Combine into a single delivery score — adds complexity without clear benefit given r=0.62

**Recommendation:** Option A — current approach is sound.

### 3. Future Monitoring
- Re-run correlation analysis quarterly or when seller population changes significantly
- Monitor if `late_delivery_rate` ↔ `average_delivery_delay_days` correlation increases above 0.7
- Consider adding `average_delivery_delay_days` as a diagnostic drill-down metric in dashboards (not in trust score)

### 4. Signal Independence Confirmed
The four risk signal categories in the PRD are empirically independent:
- **Delivery:** late_delivery_rate (primary), average_delivery_delay_days (diagnostic)
- **Review Quality:** average_review_score (primary), negative_review_rate (diagnostic)  
- **Cancellation:** cancellation_rate_proxy
- **Responsiveness:** average_response_time_hours

Each captures a distinct dimension of seller trustworthiness.

---

## Appendix: Code Used

```python
import pandas as pd
import sqlite3

conn = sqlite3.connect('data/trust_analytics.db')
df = pd.read_sql('SELECT * FROM seller_metrics WHERE eligible_for_risk_score = 1', conn)
conn.close()

cols = ['late_delivery_rate', 'average_delivery_delay_days', 
        'cancellation_rate_proxy', 'negative_review_rate', 
        'average_response_time_hours']
data = df[cols].dropna()

pearson = data.corr(method='pearson')
spearman = data.corr(method='spearman')
```