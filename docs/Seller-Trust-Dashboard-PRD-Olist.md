# PRD — Seller Behaviour & Trust Risk Dashboard
### (Learning Assignment — built on the Olist Brazilian E-Commerce Dataset)
### Status: **Decisions Locked — Ready for Build**

---

## 1. Business Problem

**Problem:**
Olist tracks seller performance, order status, and customer reviews, but this data lives in separate tables. No single view connects them, so a seller whose behaviour is slowly damaging customer trust — late deliveries, product-mismatch complaints, poor reviews — doesn't get flagged until it shows up as a pattern of bad reviews, and by then customers have already had the bad experience.

**Goal:**
Build a dashboard that combines delivery performance, order outcomes, and review sentiment per seller, so a trust-risk pattern can be spotted early instead of after the fact.

**Primary Users:** Marketplace operations / trust team (in a real company). For this assignment, "user" = whoever reviews the dashboard output — treated as a hypothetical ops analyst role.

**Success Criteria (to calculate from your own EDA, not guessed):**
- % of sellers with a declining review-score trend that get flagged by your risk score *before* their average score drops below a bad threshold (e.g. 3.0) — test your score against historical data.
- Dashboard clearly separates "consistently bad" sellers from "one bad month" sellers — validate against a sample of real seller histories.

⚠️ **Note:** Because this is a static historical dataset (2016–2018) and not a live system, "time to detect" and "DAU" style KPIs (like Riya's FreshMart example) don't apply directly. KPIs instead measure **how well the dashboard correctly separates good sellers from risky ones**, checked against manual review of a sample.

---

## 2. Stakeholders

Since this is a learning project and not a real company, these are roles you're designing *for*, not people you've interviewed:

| Type | Who (hypothetical) | Role |
|---|---|---|
| Primary user | Marketplace ops / trust analyst | Reviews flagged sellers, decides on action |
| Secondary user | Category manager | Wants a rollup by product category |
| Data owner | You (the team) | You own data cleaning and validation, since there's no real "data engineering team" to confirm fields with |
| Approver | Instructor / project reviewer | Signs off that the PRD and build match |

---

## 3. Business Impact (why this matters)

- **Operational impact:** without this dashboard, spotting a declining seller means manually cross-referencing orders, reviews, and delivery timestamps — slow and easy to miss patterns in.
- **Customer trust impact:** a seller with repeated late deliveries or mismatched products damages trust in the whole marketplace, not just that one seller.
- **Business impact:** since Olist doesn't have refund/revenue-loss data, this is framed as a *reputation and retention risk*, not a ₹/$ number — no invented revenue figure the dataset can't support.

---

## 4. Dataset & Data Source Documentation

**Source:** Kaggle — Brazilian E-Commerce Public Dataset by Olist (9 CSV files, ~100K orders, 2016–2018)

| File | Key Fields You'll Use | What It Gives You |
|---|---|---|
| `olist_orders_dataset.csv` | order_id, customer_id, order_status, order_purchase_timestamp, order_delivered_customer_date, order_estimated_delivery_date | Delivery delay = actual vs estimated date. `order_status = 'canceled'` = locked proxy for return signal. |
| `olist_order_items_dataset.csv` | order_id, product_id, **seller_id**, price, freight_value | Main join key linking orders to sellers. |
| `olist_order_reviews_dataset.csv` | review_id, order_id, review_score (1–5), review_comment_message, review_creation_date, review_answer_timestamp | Trust signal (score) + response-time proxy (creation → answer gap). Comment text is Portuguese and **out of scope for v1** (see Section 7). |
| `olist_sellers_dataset.csv` | seller_id, seller_city, seller_state | Seller identity + location, for regional rollups. |
| `olist_products_dataset.csv` | product_id, product_category_name | Category-level breakdown. |
| `olist_customers_dataset.csv` | customer_id, customer_state | Optional — only if a customer-geography view is added. |

**Refresh rate:** Not applicable — static historical dataset, not a live feed.

### 🔒 Locked Data-Mapping Decisions

The mockup (Section 10) designs around fields Olist doesn't have. These are now resolved, not open questions:

| Mockup Metric | Doesn't Exist In Olist As | Locked v1 Proxy |
|---|---|---|
| Return Rate | No returns/refunds table | `order_status = 'canceled'` ÷ total orders per seller |
| Dispute Rate | No disputes table | `review_score` of 1–2 ÷ total reviewed orders per seller |
| Sentiment (Neg/Neutral/Pos) | No sentiment classifier; comments are Portuguese | Bucketed from numeric `review_score`: 1–2 = Negative, 3 = Neutral, 4–5 = Positive |
| Avg Response Time | No customer-service response log | `review_answer_timestamp − review_creation_date` (seller's time to respond to a review) — noted as an imperfect proxy, since it measures review-response speed, not general support responsiveness |

**Why this matters:** Return Rate and Dispute Rate are now both derived from order/review data rather than independent signals — meaning they will correlate with each other by construction. This is documented as a modeling risk in Section 9, not hidden.

---

## 5. KPIs / Success Metrics

Since there's no live usage to measure (no real users logging in), KPIs are about **model/dashboard quality**, not adoption:

| Metric | How You'll Measure It | Target |
|---|---|---|
| Risk-score separation | Manually check 15–20 sellers flagged "high risk" — do their review/delivery histories actually look bad? | ≥ 80% agree with manual judgement |
| Coverage | % of sellers with enough order history (e.g. ≥5 orders) to compute a reliable score | Document what "enough data" means — don't score sellers with 1 order |
| Data completeness | % of orders successfully joined across orders → items → reviews → sellers | ≥ 95% join success (document what's lost and why) |
| Proxy correlation check | Correlation between Return Rate proxy and Dispute Rate proxy (both derived from overlapping data) | Document the correlation value — if very high, consider merging into one signal rather than double-counting |

---

## 6. User Stories

- **US-01:** As an ops analyst, I want to see sellers ranked by a trust-risk score, so I can review the worst first.
- **US-02:** As an ops analyst, I want to see *why* a seller is flagged (late deliveries? bad reviews? cancellations?), so I know what to investigate.
- **US-03:** As a category manager, I want to see risk broken down by product category, so I can tell if it's a category-wide issue or one seller.
- **US-04:** As an ops analyst, I want to filter out sellers with very few orders, so I'm not flagging someone based on one bad review.
- **US-05:** As an ops analyst, I want each flagged seller to show a recommended action (Escalate / Coach / Monitor), so the dashboard ends in a decision, not just a chart.

---

## 7. Scope

### ✅ In Scope (v1)
- Seller-level trust risk score combining: delivery delay rate + avg review score + review score trend + cancellation-rate proxy (returns) + low-score proxy (disputes)
- Ranked list of sellers by risk, with status badges (Trusted / Watchlist / High Risk)
- Drill-down: seller's order history, review history, delivery performance, sentiment breakdown (score-bucketed)
- Category-level rollup + seller behaviour segments (Reliable / Inconsistent / Return-Prone / High-Risk tiers)
- Recommended action per flagged seller (Escalate / Coach / Monitor), with supporting evidence

### ❌ Out of Scope (v1)
- Real-time updates (data is static/historical)
- Predicting *future* risk (this is descriptive, not predictive, in v1)
- True return/refund tracking or dispute tracking (proxied per Section 4 — not real data)
- NLP/translated sentiment analysis on Portuguese review text (v1 uses numeric score buckets only)
- Any live "intervention logging" (no real ops team to log actions against)

---

## 8. Data Workflow

1. **Ingest:** Load orders, order_items, order_reviews, sellers, products CSVs.
2. **Join:** `order_items.seller_id` → `orders` → `order_reviews` → `products`. Validate join success rate.
3. **Clean:** Handle missing review scores (`[VERIFY: check NULL rate]`), parse date fields, compute delivery delay = `order_delivered_customer_date − order_estimated_delivery_date`.
4. **Feature engineering per seller:**
   - Return Rate proxy = % orders `canceled`
   - Dispute Rate proxy = % reviews scored 1–2
   - Sentiment buckets = review_score mapped to Neg/Neutral/Pos
   - Response Time proxy = avg(`review_answer_timestamp − review_creation_date`)
   - Delivery delay rate, review score trend (recent vs older), order volume (for confidence weighting)
5. **Score:** Combine features into a single Trust Score (0–100) — document weighting logic and rationale. Check correlation between Return Rate and Dispute Rate proxies before finalizing weights (see Section 5).
6. **Segment:** Bucket sellers into Reliable / Inconsistent / Return-Prone / High-Risk tiers using thresholds from the wireframe (Section 10).
7. **Visualize:** Streamlit dashboard matching the 5-section structure in Section 10.

---

## 9. Risks & Assumptions

| Risk / Assumption | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Return Rate and Dispute Rate proxies are both derived from overlapping data (cancellations, low scores) | High | Medium — risk of double-counting the same underlying signal in the composite score | Check correlation between the two proxies before finalizing score weights; consider merging if highly correlated |
| Review comments are in Portuguese, sentiment uses numeric score only | Certain (by design for v1) | Low — score-bucketed sentiment is coarser than true text sentiment | Documented as a v1 scope decision, not a gap; flag as v2 opportunity |
| Response Time proxy measures review-reply speed, not general support responsiveness | Certain | Low-Medium — may not reflect true customer service quality | State this limitation explicitly wherever Response Time is shown |
| Sellers with very few orders get unreliable scores | High | Medium — could unfairly flag a seller with 1 bad review | Set a minimum order-count threshold before a seller gets scored |
| Static dataset means no way to validate "did the flag actually help" | Certain | Low — known limitation of a historical/learning dataset | Be upfront that this is a retrospective analysis, not a live monitoring tool |

---

## 10. Dashboard Wireframe (Mock UX)

**Live mockup:** https://seller-trust-dashboard.vercel.app/ — "TrustLens," v1.1

The mockup is organized in investigation order, not menu order — overview, then cause analysis, then per-seller evidence, then portfolio view, then decision:

1. **Trust Overview** — marketplace-wide baseline. 4 KPI cards (Avg Trust Score, Return Rate, Negative Sentiment %, At-Risk Seller count), a trust-score distribution histogram, and a "Top Trust-Eroding Behaviours" ranking chart.
2. **Trust vs. Behaviour Signals** — cohort comparison table (high-trust vs low-trust sellers), a trust-score trend line over time, a return-rate-vs-trust-score scatter plot, and a behaviour-correlation bar chart.
3. **Seller Scorecard** — sortable table of all sellers (Trust Score, Return Rate, Sentiment, Response Time, Dispute Rate), with a click-to-expand detail panel per seller.
4. **Behaviour Segments** — portfolio view grouping sellers into 4 tiers (Reliable / Inconsistent / Return-Prone / High-Risk) with a stacked bar showing tier composition.
5. **Trust-Risk Actions** — action cards per flagged seller with a recommended tier (Escalate / Coach / Monitor) and supporting evidence.

**How this maps to the PRD:**
- Section 1's 4 KPI cards = this PRD's Section 5 metrics, using the locked proxies from Section 4.
- Section 2's correlation view is where the Section 9 proxy-overlap risk should be visually checked, not just documented.
- Section 3's Scorecard directly implements US-01 and US-02.
- Section 4's Behaviour Segments implements the tiers referenced in Section 7's scope.
- Section 5's Action Cards implement US-05.

**Gaps between the mockup and what v1 can actually deliver** (document these, don't silently build around them):
- The mockup's header says data sources include "Seller Ops pipelines" — no such pipeline exists here; all 4 KPIs are proxy-derived per Section 4.
- The mockup shows true Neg/Neutral/Pos sentiment classification; v1 only has score-bucketed sentiment, which is coarser.
- The mockup's "Top Cited Return Reasons & Review Keywords" panel implies text mining on review comments — out of scope for v1 (Portuguese NLP, Section 7).

---

## 11. Validation Checklist

- [x] Problem statement matches what the dataset can actually support (returns gap addressed)
- [x] Every KPI has a method and target
- [x] Data source table lists real file/column names, not assumed ones
- [x] Data gap (no returns/disputes table) explicitly documented, with locked proxies
- [x] User stories follow Role + Action + Benefit
- [x] Scope explicitly excludes real-time, predictive, and NLP-sentiment features
- [x] Risk table includes the proxy-overlap and Portuguese-text risks
- [x] No aspirational language ("should be useful," "real-time," "all stakeholders")
- [x] Wireframe included, mapped to PRD sections, gaps documented
- [ ] Stakeholder alignment review completed — **still needs instructor/reviewer sign-off**
- [x] A non-technical reader can tell what this dashboard does and why

---

### What's left before this is fully submission-ready
1. Run profiling on the CSVs to replace the one remaining `[VERIFY]` (NULL rate on review_score) with a real number.
2. Get the instructor/reviewer sign-off checkbox closed.
3. Optional: run the correlation check between Return Rate and Dispute Rate proxies once the data is loaded, and report the result back into Section 9.
