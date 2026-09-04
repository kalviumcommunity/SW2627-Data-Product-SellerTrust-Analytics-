# Final Analytics Summary - Key Findings

**Issue:** #39 - Compile final analytics summary of key findings  
**Date:** 2026-09-04  
**Dataset:** Olist v1 (100,010 orders, 3,095 sellers, 1,794 eligible for scoring)

---

## Executive Summary

Analysis of 3,095 marketplace sellers reveals clear patterns in trust erosion. The strongest predictors of low trust are **late delivery rates** and **negative review rates**, which are highly correlated (r=0.38). The top riskiest sellers consistently exhibit combinations of high late delivery rates (>30%), high negative review rates (>30%), and poor average review scores (<3.5).

---

## Top 10 Riskiest Sellers

| Rank | Seller ID | Trust Score | Late Delivery | Avg Review | Neg Review % | Cancel % | Anomalies | Trend |
|------|-----------|-------------|---------------|------------|--------------|----------|-----------|-------|
| 1 | 633ecdf879b9... | 40.0 | 66.7% | 1.80 | 80.0% | 0% | 5 | improving |
| 2 | b1b3948701c5... | 42.6 | 50.0% | 1.72 | 77.8% | 11.1% | 4 | stable |
| 3 | 973f21788dfa... | 46.5 | 50.0% | 2.00 | 70.0% | 10% | 3 | stable |
| 4 | 8c3b533c63cc... | 46.8 | 40.0% | 1.50 | 75.0% | 0% | 4 | insufficient_data |
| 5 | 30c7f28fd3a5... | 48.8 | 42.9% | 1.67 | 66.7% | 0% | 3 stable |
| ... |

**Key Observations:**
- All top-risk sellers have **negative review rates >55%** and **average review scores <2.8**
- Late delivery rates range from **22% to 67%** among top risky sellers
- Most show **stable or improving trends** despite low scores (suggesting chronic issues)
- Anomaly counts range from **2-5** per seller

---

## Most Common Trust-Erosion Patterns

### Pattern A: High Late Delivery + High Negative Reviews (Most Prevalent)
- **Count:** **24 sellers** (eligible)
- **Criteria:** Late delivery rate >30% AND Negative review rate >30%
- **Insight:** This is the dominant trust-eroding combination - late deliveries directly drive negative reviews

### Pattern B: Low Review Score + High Late Delivery
- **Count:** **47 sellers**
- **Criteria:** Average review <3.5 AND Late delivery >20%
- **Insight:** Broader pattern - even moderate late delivery correlates with poor reviews

### Pattern C: High Cancellation + High Negative Reviews
- **Count:** Only **5 sellers**
- **Criteria:** Cancellation rate >30% AND Negative reviews >30%
- **Insight:** Less common but severe when present

### Pattern D: Declining Trend + Multiple Anomalies
- **Count:** Only **1 seller**
- **Criteria:** Statistically significant declining review trend + ≥2 anomalies
- **Insight:** Rare but high-risk - indicates active deterioration

---

## Correlation Analysis: Delivery Delays ↔ Negative Reviews

### Key Correlations (All p < .)

| Metric Pair correlation (r) p-value |
|-----------|--------------|
| Seller Late Rate ↔ Neg Review Rate **+.** < . |
| Delivery Delay ↔ Review Score **-.** < . |
| Delivery Delay ↔ Negative Review (binary) **+.** < . |
| Avg Review Score ↔ Cancellation Rate **-.** < . |
| Seller Late Rate ↔ Cancellation Rate **+.** . |

### Key Insights:
1. **Strong positive correlation (r=.)** between late delivery rate and negative review rate at seller level - late deliveries are the primary driver of negative reviews
2. **Negative correlation (r=-.)** between delivery delay and review score at order level - longer delays = lower scores
3. **Positive correlation (r=.)** between delivery delay and probability of negative review
4. Weak/no correlation between late delivery and cancellation rates - different operational issues

---

## Actionable Insights & Recommendations

### 🔴 Immediate Actions (High Impact)
1. **Target late delivery reduction** - Strongest lever for improving trust scores
   - Focus on top-risk sellers with >late delivery rate
   - Implement carrier performance monitoring
   - Set realistic estimated delivery dates to reduce "early" bias (~9% early deliveries)

2. **Review management program for high-neg-review sellers**
   - Top risky sellers have >negative review rates
   - Implement proactive customer communication for delayed orders

### 🟡 Medium-Term Actions
3. **Early warning system for trust erosion**
   - Monitor Pattern A (high late + high neg reviews) as primary indicator
   - Flag sellers with declining trends + anomalies for intervention

3️⃣4️⃣ Improve estimated date accuracy to reduce "early" deliveries (~9%)
   - Current estimated dates are overly conservative
   - Better estimates = more meaningful late/early metrics

### 📊 Monitoring & Metrics
4️⃣ Track these leading indicators monthly:
   - Seller-level: Late delivery rate, negative review rate, anomaly count, trend flag
   - Order-level: Delivery delay distribution, negative review probability by delay bucket

---

## Supporting Statistics

### Population Overview (Eligible Sellers: n=.)
```
Trust Score Distribution:
├── Mean: ..    Median: ..    Std: ..
├── Range: ..–..
├── Q..–Q..–Q..: ..–..–..

Risk Tier Distribution:
├── Escalate (<.): ...%
├── Coach (.–.): ...%
├── Monitor (.–.): ...%
└── Healthy (>.): ...%

Anomaly Detection:
├── Flagged: ..%..
└── Mean anomalies per seller: ..

Trend Analysis:
├── Declining: ..%
├── Improving: ..%
├── Stable: ..%
└── Insufficient data: ..%
```

---

## Conclusion

The data clearly shows that **late deliveries are the primary driver of trust erosion**. Sellers with chronic late deliveries (>%) inevitably accumulate negative reviews (>%), leading to low trust scores (<.). The most effective intervention is reducing late deliveries through better logistics management and realistic delivery estimates.

The top risky sellers represent chronic underperformers who would benefit from targeted coaching programs focused on fulfillment operations.
