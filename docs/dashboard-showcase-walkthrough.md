# Dashboard Showcase Walkthrough

## Demo Objective

Show how the Seller Trust Analytics dashboard helps an operations analyst move from a marketplace-level risk overview to seller-level evidence and recommended action. The demo should make it clear that the dashboard is descriptive and retrospective, using the static Olist dataset and the PRD-approved proxy signals.

## Recording Checklist

- Start from a clean browser tab with the Streamlit app open.
- Confirm the sidebar filters are visible: seller search, risk tier, category, and refresh timestamp.
- Record the full flow in this order: Trust Overview, Trust vs. Behaviour Signals, Seller Scorecard, Behaviour Segments, Trust-Risk Actions.
- Demonstrate one filter change, such as selecting High-Risk sellers or searching for a seller ID.
- Show one empty or narrowed filter state to explain graceful error handling.
- Keep the screen capture around 3-5 minutes for the final showcase.

## Presentation-Ready Demo Flow

1. Open the dashboard and introduce the problem: seller behaviour signals are spread across orders, reviews, products, and seller tables, so the dashboard combines them into one trust-risk view.
2. Use the sidebar to explain that the dashboard can be filtered by seller ID, risk tier, and product category.
3. Walk through the five dashboard sections in order, ending with recommended actions.
4. Close by explaining the key limitation: Olist is a static historical dataset, so the dashboard supports retrospective trust analysis rather than live intervention tracking.

## Section Talking Points

### 1. Trust Overview

- Introduce the four KPI cards: Avg Trust Score, Return Rate %, Negative Sentiment %, and At-Risk Sellers.
- Explain that Return Rate is the PRD-approved cancellation-rate proxy because the Olist dataset does not contain a true returns table.
- Use this section as the marketplace baseline before drilling into individual sellers.

### 2. Trust vs. Behaviour Signals

- Use the scatter plot to show the relationship between return-rate proxy and trust score.
- Use the correlation heatmap to explain whether risk signals overlap or double-count the same behaviour.
- Use the cohort comparison table to contrast high-trust and low-trust sellers using delivery, review, and cancellation behaviour.
- Mention the monthly trend visuals as evidence of seller trust erosion over time.

### 3. Seller Scorecard

- Show the sortable seller table with trust score, risk tier, review score, negative review rate, late delivery rate, and return proxy.
- Demonstrate how filters narrow the table to a specific risk tier, seller, or category.
- Open the anomaly detail expander when available to show what changed and when.

### 4. Behaviour Segments

- Explain the four seller tiers: Reliable, Inconsistent, Return-Prone, and High-Risk.
- Use the segment composition chart to show how sellers are distributed across behaviour groups.
- Point out that low-volume sellers are handled carefully so one bad order does not unfairly define a seller.

### 5. Trust-Risk Actions

- Show action cards for flagged sellers.
- Explain the three recommended actions: Escalate, Coach, and Monitor.
- Use the evidence bullets to show that the dashboard ends in an operational decision, not just a chart.

## Edge Cases and Limitations to Acknowledge

- The dataset is static from 2016-2018, so this is not a real-time monitoring system.
- Returns and disputes are not directly available in Olist; cancellations and low review scores are used as documented proxies.
- Sentiment is score-bucketed from review scores, not NLP-based Portuguese text analysis.
- Sellers with very low order counts can have unstable scores, so the dashboard uses eligibility and confidence checks.
- Missing delivery timestamps and missing reviews are handled in the pipeline, but they still reduce confidence in some seller histories.

## Suggested Closing Line

This dashboard turns scattered seller, order, delivery, and review data into a clear trust-risk workflow: detect the risky seller, understand the behaviour, and decide the next action.

