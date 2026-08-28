# Trust score distribution and segmentation threshold validation

## Scope

This analysis uses all sellers with a numeric `trust_score` and checks whether the 4-tier segmentation (`High-Risk`, `Return-Prone`, `Inconsistent`, `Reliable`) has meaningful group sizes.

## Descriptive statistics computed

`src/thresholds.py::compute_trust_score_distribution()` now computes:

- Mean trust score
- Median trust score
- Population standard deviation (`ddof=0`)
- Quartile breakpoints (`Q1`, `Q2`, `Q3`)

These quartile breaks are also used as fallback segmentation thresholds when custom thresholds create very small tiers.

## Tier-balance validation

`src/thresholds.py::validate_segmentation_thresholds()` validates the tier split and enforces:

- No tier below 5% of scored sellers (`min_share=0.05`)

If any tier is below 5%, thresholds are automatically adjusted to score quartiles (`Q1`, `Q2`, `Q3`) and re-validated.

## Findings

- A fixed threshold set can create very small groups (for example, nearly all sellers in one tier).
- Quartile-based thresholds provide a balanced segmentation baseline and prevent undersized tiers in normal distributions.
- The validator now adjusts imbalanced thresholds to quartile cutoffs so tier composition remains operationally meaningful.
