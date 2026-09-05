# Action Thresholds for Seller Risk Tiers

**Issue:** #24 - Define action thresholds with industry benchmarks  
**Date:** 2024-09-05  
**Sources:** Amazon Seller Central, Walmart Marketplace Learn, eBay Seller Standards, Data Distribution Analysis

---

## Executive Summary

This document defines three action tiers for seller risk management based on industry benchmarks from major e-commerce marketplaces (Amazon, Walmart, eBay) calibrated with actual data distributions from the Olist dataset. Thresholds are configurable in `src/config/thresholds.yaml`.

| Tier | Action | Description |
|------|--------|-------------|
| **ESCALATE** | Immediate intervention | At/above marketplace suspension thresholds or extreme outliers |
| **COACH** | Targeted improvement | Between internal target and escalation threshold |
| **MONITOR** | Routine monitoring | Below internal targets (healthy performance) |

---

## Industry Benchmark Sources

### 1. Amazon Seller Central (2026)
| Metric | Suspension Threshold | Internal Target (50%) | Measurement Window |
|--------|---------------------|----------------------|-------------------|
| Order Defect Rate (ODR) | **1.0%** | 0.5% | Rolling 60 days |
| Pre-Fulfillment Cancellation Rate | **2.5%** | 1.25% | Rolling 7 days |
| Late Shipment Rate | **4.0%** | 2.0% | Rolling 10-30 days |
| Valid Tracking Rate | > 95% | > 97.5% | Rolling 30 days |
| On-Time Delivery Rate | > 90% | > 95% | Rolling 30 days |

**Source:** [Amazon Order Performance Program Policy](https://sellercentral.amazon.com/help/hub/reference/external/GGJVNFDXQT8C3RA8)

### 2. Walmart Marketplace (2026)
| Metric | Standard | Measurement Window |
|--------|----------|-------------------|
| Cancellation Rate | **<= 2%** | Rolling 30 days |
| On-Time Delivery Rate | **>= 90%** | Rolling 30 days |
| Valid Tracking Rate | **>= 99%** | Rolling 30 days |
| Seller Response Rate | **>= 95%** | Rolling 30 days |
| Return Rate | **<= 6%** | Rolling 60 days |
| Item Not Received Rate | **<= 2%** | Rolling 60 days |
| Negative Feedback Rate | **<= 2%** | Rolling 60 days |

**Source:** [Walmart Seller Performance Standards](https://marketplacelearn.walmart.com/guides/Policies%20&%20standards/Performance/Seller-performance-standards)

### 3. eBay Global Seller Standards (2026)
| Metric | Minimum Standard | Top Rated Standard | Measurement Window |
|--------|-----------------|-------------------|-------------------|
| Transaction Defect Rate | **<= 2%** | <= 0.5% | Evaluation period |
| Cases Closed Without Resolution | <= 2 or 0.3% | <= 2 or 0.3% | Evaluation period |
| Late Shipment/Delivery Rate | No minimum | <= 3-5% | Evaluation period |

**Source:** [eBay Global Seller Performance Policy](https://www.ebay.com/help/policies/selling-policies/global-seller-performance-policy?id=4351)

---

## Data Distribution Analysis (Olist Dataset - 1,794 Eligible Sellers)

| Metric | Mean | Median | 75th Percentile | Max |
|--------|------|--------|-----------------|-----|
| Cancellation Rate Proxy | 0.77% | 0.00% | 0.00% | 38.5% |
| Negative Review Rate | 14.5% | 12.5% | 20.0% | 94.7% |
| Late Delivery Rate | 7.7% | 5.9% | 11.7% | 66.7% |
| Average Review Score | 4.12 | 4.17 | 4.42 | 5.00 |

**Key Insight:** Industry "negative feedback rate" (1-2 star) thresholds of 1-2% are much stricter than our observed negative review rate (14.5% mean). This is because marketplace metrics typically exclude neutral (3-star) reviews and only count specific defect types. Our metric includes all 1-2 star reviews.

---

## Final Mapped Thresholds

| Metric | MONITOR (Healthy) | COACH (Needs Improvement) | ESCALATE (Critical) | Basis |
|--------|-------------------|---------------------------|---------------------|-------|
| **Cancellation Rate Proxy** | < 1.25% | 1.25% - 2.5% | >= 2.5% | Amazon suspension threshold |
| **Negative Review Rate** | < 15% | 15% - 25% | >= 25% | Data-driven (mean to 75th+ percentile) |
| **Late Delivery Rate** | < 5% | 5% - 10% | >= 10% | Data-driven (median to 75th+ percentile) |
| **Average Review Score** | >= 3.8 | 3.5 - 3.8 | < 3.5 | Quality threshold |

### Rationale

1. **Cancellation Rate Proxy** (0.77% mean, 0% median)
   - Amazon: 2.5% suspension, 1.25% internal target
   - Walmart: 2% standard
   - **Escalate at 2.5%** (Amazon suspension threshold)
   - **Coach at 1.25%** (50% of Amazon threshold)

2. **Negative Review Rate** (14.5% mean, 20% 75th percentile)
   - Industry benchmarks (1-2%) are for specific defect types, not all 1-2 star reviews
   - **Escalate at 25%** (above 75th percentile - extreme outliers)
   - **Coach at 15%** (around mean - needs improvement)

3. **Late Delivery Rate** (7.7% mean, 11.7% 75th percentile)
   - Amazon: 4% Late Shipment Rate (ship-date based, stricter)
   - Walmart: 90% OTD = 10% late delivery max
   - **Escalate at 10%** (above 75th percentile)
   - **Coach at 5%** (between median and 75th percentile)

4. **Average Review Score** (4.12 mean)
   - **Escalate at < 3.5** (approaching negative territory)
   - **Coach at 3.5-3.8** (below "good" threshold of 4.0)

---

## Configuration

Thresholds are defined in `src/config/thresholds.yaml`:

```yaml
# Action thresholds for seller risk tiers
# Based on industry benchmarks: Amazon, Walmart, eBay (2026) + data distribution

action_tiers:
  escalate:
    cancellation_rate_proxy: 0.025    # 2.5% - Amazon suspension threshold
    negative_review_rate: 0.250       # 25% - above 75th percentile (data-driven)
    late_delivery_rate: 0.100         # 10% - above 75th percentile (data-driven)
    average_review_score: 3.5         # Below 3.5 = approaching negative

  coach:
    cancellation_rate_proxy: 0.0125   # 1.25% - 50% of Amazon threshold
    negative_review_rate: 0.150       # 15% - around mean (data-driven)
    late_delivery_rate: 0.050         # 5% - between median and 75th percentile
    average_review_score: 3.8         # Below 3.8 = below "good"

# Trust score component weights (from trust_score.py)
trust_score_weights:
  delivery_performance: 0.30
  review_quality: 0.30
  cancellation_score: 0.20
  negative_review_score: 0.20

# Eligibility
min_orders_for_risk_score: 5

# Anomaly detection thresholds
anomaly_detection:
  zscore_threshold: 3.0
  iqr_multiplier: 1.5
```

---

## Implementation

### Risk Tier Assignment Logic

```python
def assign_risk_tier(row: pd.Series) -> str:
    """Assign risk tier based on action thresholds."""
    esc = THRESHOLDS["action_tiers"]["escalate"]
    coach = THRESHOLDS["action_tiers"]["coach"]

    def check_ge(val, threshold):
        if pd.isna(val):
            return False
        return val >= threshold

    def check_lt(val, threshold):
        if pd.isna(val):
            return False
        return val < threshold

    escalate = (
        check_ge(row["cancellation_rate_proxy"], esc["cancellation_rate_proxy"])
        or check_ge(row["negative_review_rate"], esc["negative_review_rate"])
        or check_ge(row["late_delivery_rate"], esc["late_delivery_rate"])
        or check_lt(row["average_review_score"], esc["average_review_score"])
    )

    coach_tier = (
        check_ge(row["cancellation_rate_proxy"], coach["cancellation_rate_proxy"])
        or check_ge(row["negative_review_rate"], coach["negative_review_rate"])
        or check_ge(row["late_delivery_rate"], coach["late_delivery_rate"])
        or check_lt(row["average_review_score"], coach["average_review_score"])
    )

    if escalate:
        return "ESCALATE"
    elif coach_tier:
        return "COACH"
    else:
        return "MONITOR"
```

### Current Distribution (from 1,794 eligible sellers)

| Tier | Count | Percentage | Avg Cancellation | Avg Neg Review | Avg Late Delivery | Avg Review Score |
|------|-------|------------|------------------|----------------|-------------------|------------------|
| MONITOR | 550 | 31% | 0.01% | 5.4% | 1.0% | 4.48 |
| COACH | 494 | 28% | 0.15% | 13.7% | 5.6% | 4.13 |
| ESCALATE | 750 | 42% | 1.73% | 21.6% | 14.1% | 3.84 |

*Run `python -c "from src.risk_tier import *; from src.pipeline import *; ..."` to comput
