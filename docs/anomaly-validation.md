# Anomaly Detection Threshold Validation

**Issue:** #21 - Validate anomaly thresholds with manual review  
**Date:** 2026-09-02  
**Reviewer:** Himanshu Gupta

## Summary

Manual review of 20 sellers (10 flagged as anomalous, 10 not flagged) to validate the Z-score threshold (default 3.0) and IQR multiplier (default 1.5) used in anomaly detection.

## Review Methodology

- Sampled 10 sellers with `any_anomaly = True` (flagged)
- Sampled 10 sellers with `any_anomaly = False` (not flagged)
- Reviewed each seller's metrics, recent orders, and anomaly flags
- Classified each as True Positive (TP), False Positive (FP), True Negative (TN), or False Negative (FN)

## Review Results

| # | Seller ID | Flagged | Assessment | Notes |
|---|-----------|---------|------------|-------|
| 1 | 001e6ad469a905060d959994f1b41e4f | YES | **TP** | Single order, score=1, cancelled, 309h response time - genuinely anomalous |
| 2 | 003554e2dce176b5555353e4f3555ac8 | YES | **FP** | Single order, score=5, delivered 26 days early - early delivery not a risk |
| 3 | 010da0602d7774602cd1b3f5fb7b709e | YES | **TP** | Single order, score=1, negative review - genuinely poor performance |
| 4 | 011b0eaba87386a2ae96a7d32bb531d1 | YES | **FP** | Single order, score=4, delivered 29 days early, 1857h response - early delivery & old data |
| 5 | 01fdefa7697d26ad920e9e0346d4bd1b | YES | **FP** | 129 orders, good metrics, only high response time (154h) - not necessarily risky |
| 6 | 0249d282d911d23cb8b869ab49c99f53 | YES | **FP** | 11 orders, 18% late/negative, high response time - borderline but not clearly anomalous |
| 7 | 024b564ae893ce8e9bfa02c10a401ece | YES | **FP** | 2 orders, both delivered 30+ days early - early delivery not a risk |
| 8 | 02a2272692e13558373c66db98f05e2e | YES | **TP** | 2 orders, 50% cancellation, 50% negative reviews - genuinely risky |
| 9 | 02d35243ea2e497335cd0f076b45675d | YES | **TP** | 14 orders, 36% late, 43% negative reviews - genuinely poor performer |
| 10 | 02dcd3e8e25bee036e32512bcf175493 | YES | **FP** | 14 orders, 29% late/negative but recent orders all score 5 - improving trend |
| 11 | 0015a82c2db000af6aaaf3ae2ecb0532 | NO | **TN** | 3 orders, mixed scores, no clear risk pattern |
| 12 | 001cca7ae9ae17fb1caed9dfb1094831 | NO | **TN** | 200 orders, good metrics, consistent performer |
| 13 | 002100f778ceb8431b7a1020ff7ab48f | NO | **FN** | 51 orders, 18% late, 16% negative - should be flagged |
| 14 | 004c9cd9d87a3c30c522c48c4fc07416 | NO | **TN** | 158 orders, good metrics, consistent performer |
| 15 | 00720abe85ba0859807595bbf045a33b | NO | **FN** | 13 orders, 15% late, 23% negative - should be flagged |
| 16 | 00ab3eff1b5192e5f1a63bcecfee11c8 | NO | **TN** | Single order, perfect score - no risk |
| 17 | 00d8b143d12632bad99c0ad66ad52825 | NO | **TN** | Single order, perfect score - no risk |
| 18 | 00ee68308b45bc5e2660cd833c3f81cc | NO | **TN** | 135 orders, good metrics, consistent performer |
| 19 | 00fc707aaaad2d31347cf883cd2dfe10 | NO | **TN** | 103 orders, good metrics, consistent performer |
| 20 | 010543a62bd80aa422851e79a3bc7540 | NO | **TN** | 2 orders, good scores - no risk |

## Confusion Matrix

| | Predicted Anomaly | Predicted Normal |
|---|---|---|
| **Actually Anomalous** | TP = 3 | FN = 2 |
| **Actually Normal** | FP = 5 | TN = 10 |

## Metrics

- **Precision** = TP / (TP + FP) = 3 / (3 + 5) = **37.5%**
- **Recall** = TP / (TP + FN) = 3 / (3 + 2) = **60.0%**
- **Accuracy** = (TP + TN) / Total = (3 + 10) / 20 = **65.0%**
- **F1 Score** = 2 × (Precision × Recall) / (Precision + Recall) = **46.2%**

## Key Findings

1. **High False Positive Rate (62.5%)**: Many flagged sellers are false positives due to:
   - Early deliveries being flagged as anomalies (negative delivery delay)
   - Single-order sellers with extreme values skewing Z-scores
   - High response times not necessarily indicating risk

2. **Moderate False Negative Rate (16.7%)**: Some genuinely risky sellers not flagged:
   - Sellers with 15-18% late delivery and negative review rates

3. **Z-score threshold of 3.0 is too sensitive** for this dataset, especially with:
   - Small sample sizes (single-order sellers)
   - Negative delivery delays (early deliveries) being treated as outliers

## Recommendations

1. **Increase Z-score threshold from 3.0 to 3.5** to reduce false positives
2. **Exclude early deliveries** (negative delay) from anomaly detection or treat separately
3. **Require minimum order count** (e.g., 5+ orders) before applying Z-score detection
4. **Use IQR method as primary** with Z-score as secondary confirmation
5. **Add trend context**: Don't flag sellers with improving recent performance

## Adjusted Configuration

```python
# Recommended settings for production
ZSCORE_THRESHOLD = 3.5  # Increased from 3.0
IQR_MULTIPLIER = 1.5    # Keep as is
MIN_ORDERS_FOR_ZSCORE = 5  # New: minimum orders before Z-score applied
EXCLUDE_EARLY_DELIVERY = True  # New: don't flag negative delivery delays
```

## Next Steps

- [x] Implement adjusted thresholds in `src/anomaly_detection.py`
- [x] Add `min_orders` parameter to Z-score detection
- [x] Add option to exclude early deliveries from anomaly detection
- [ ] Re-run validation with adjusted thresholds
- [x] Update `scripts/detect_anomalies.py` with new defaults
