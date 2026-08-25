# Seller Trust Analytics — 12-Day Sprint Plan

**Project:** Seller Behaviour & Trust Risk Dashboard  
**Dataset:** Olist Brazilian E-Commerce (Kaggle)  
**Stack:** Python, Pandas, NumPy, SQLite, Streamlit, Plotly  
**Status:** Day 1–9 data pipeline foundation complete  

---

## Team Assignments

| Member | Role | Responsibilities |
|--------|------|------------------|
| **Himanshu** | Data & Research | Data sourcing, schema validation, statistical analysis, research-backed metric definitions |
| **Gourish** | Python & Data Processing | Pipeline development, ETL scripts, SQL integration, data cleaning, automation |
| **Hrithik** | Analysis & Visualization | Streamlit dashboard, Plotly charts, KPI cards, UI/UX, interactive components |

---

## Coding Task Board

### Day 1 — Trust Score Engine

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#1** | Gourish | Implement `calculate_trust_score()` in `src/trust_score.py` — combine delivery delay rate, avg review score, cancellation rate proxy, and negative review rate into a composite 0–100 score per seller. Document weighting rationale in code comments. |
| **#2** | Himanshu | Define statistical thresholds for score normalization — compute percentile ranks for each metric across all 3,095 sellers. Write `src/thresholds.py` with functions to derive cutoffs from data (not hardcoded). |
| **#3** | Hrithik | Scaffold Streamlit app in `app/main.py` — set up page config, sidebar layout, and placeholder tabs for Overview / Seller Scorecard / Risk Alerts. Verify `streamlit run app/main.py` launches cleanly. |

---

### Day 2 — Seller Segmentation

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#4** | Gourish | Implement `segment_sellers()` in `src/segmentation.py` — bucket sellers into Reliable / Inconsistent / Return-Prone / High-Risk tiers based on trust score thresholds. Output a `seller_segments.csv` to `data/processed/`. |
| **#5** | Himanshu | Analyze score distribution across sellers — compute mean, median, std, and quartile breaks for the trust score. Validate that segmentation thresholds produce meaningful group sizes (no tier with <5% of sellers). |
| **#6** | Hrithik | Build Trust Overview section in the dashboard — 4 KPI cards (Avg Trust Score, Return Rate %, Negative Sentiment %, At-Risk Sellers Count) using `st.metric()`. Pull data from `seller_metrics.csv`. |

---

### Day 3 — SQL Layer Setup

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#7** | Gourish | Create SQLite database in `data/trust_analytics.db` — write `src/sql_loader.py` to load `seller_order_fact.csv` and `seller_metrics.csv` into normalized tables. Add table creation scripts with proper indexes on `seller_id` and `order_id`. |
| **#8** | Himanshu | Write SQL views for analytics — create `vw_seller_trust_metrics` (seller-level rollup), `vw_category_risk` (risk by product category), `vw_monthly_trends` (time-series aggregation). Store in `sql/views.sql`. |
| **#9** | Hrithik | Implement sidebar filters in Streamlit — add seller search (text input), risk tier dropdown, and category filter. Connect filters to query the SQLite database and update displayed data dynamically. |

---

### Day 4 — Risk Signal Analysis

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#10** | Gourish | Implement risk signal decomposition in `src/risk_signals.py` — for each flagged seller, compute per-signal contributions (delivery delay contribution, review contribution, cancellation contribution). Output `seller_risk_breakdown.csv`. |
| **#11** | Himanshu | Perform correlation analysis between risk signals — compute Pearson/Spearman correlation matrix for delivery delay, cancellation rate, negative review rate, and response time. Check for double-counting risk (document in `docs/correlation-analysis.md`). |
| **#12** | Hrithik | Build Trust vs. Behaviour Signals section — create a Plotly scatter plot (return rate vs. trust score), a correlation heatmap, and a cohort comparison table (high-trust vs low-trust sellers). |

---

### Day 5 — Time-Series & Rolling Metrics

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#13** | Gourish | Implement rolling metrics in `src/rolling_metrics.py` — compute 30-day rolling average review score, rolling return rate, and rolling late delivery rate per seller. Handle sellers with sparse order history gracefully. |
| **#14** | Himanshu | Implement trend detection — for each seller, compute slope of review score over time using linear regression. Flag sellers with statistically significant declining trends. Write results to `seller_trends.csv`. |
| **#15** | Hrithik | Build time-series visualizations — line chart of seller trust score over time, stacked bar of sentiment distribution by month, and a seller performance decay chart. Use Plotly with custom hover tooltips. |

---

### Day 6 — Anomaly Detection

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#16** | Gourish | Implement anomaly detection in `src/anomaly_detection.py` — use IQR method and Z-score to flag sudden spikes in return rate, drops in review score, and delivery delay surges. Output `seller_anomalies.csv`. |
| **#17** | Himanshu | Validate anomaly thresholds — compute false-positive rate by manually reviewing a sample of 20 flagged vs non-flagged sellers. Adjust Z-score threshold (default 3.0) if needed. Document results. |
| **#18** | Hrithik | Build anomaly alert UI — add danger indicator badges (red/yellow/green) to the Seller Scorecard table. Show anomaly details (what spiked, when) in an expandable row section. |

---

### Day 7 — Action Recommendations

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#19** | Gourish | Implement recommendation engine in `src/actions.py` — map seller segments and risk signals to recommended actions: Escalate (High-Risk + declining trend), Coach (Inconsistent + fixable signals), Monitor (isolated bad month). Output `seller_actions.csv`. |
| **#20** | Himanshu | Define action thresholds — research industry benchmarks for e-commerce seller risk. Map "Return Rate > X%" and "Negative Review Rate > Y%" to action tiers. Document sources in `docs/action-thresholds.md`. |
| **#21** | Hrithik | Build Trust-Risk Actions section — display action cards per flagged seller with recommended tier (Escalate / Coach / Monitor), supporting evidence bullets, and a visual severity indicator. |

---

### Day 8 — Dashboard Integration

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#22** | Gourish | Implement `src/data_export.py` — add CSV export for filtered seller reports and a function to regenerate all processed outputs from raw data. Support `--full-refresh` flag in `scripts/run_pipeline.py`. |
| **#23** | Hrithik | Integrate all 5 dashboard sections into a single Streamlit app — Overview, Behaviour Signals, Seller Scorecard, Behaviour Segments, Trust-Risk Actions. Ensure tab navigation works and data flows correctly between sections. |
| **#24** | Himanshu | Cross-validate dashboard outputs against raw data — run 10 manual spot-checks (pick random sellers, verify their displayed metrics match the raw CSVs). Document any discrepancies. |

---

### Day 9 — Performance & Edge Cases

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#25** | Gourish | Optimize pipeline performance — profile `run_pipeline.py` with `cProfile`, identify bottlenecks. Cache intermediate DataFrames using `@functools.lru_cache` or Parquet format for faster reload. |
| **#26** | Hrithik | Handle edge cases in Streamlit — add error states for empty filter results, loading spinners for slow queries, and graceful fallback when `data/processed/` files are missing. Add session state for filter persistence across tab switches. |
| **#27** | Himanshu | Document edge cases discovered — sellers with 0 reviews, sellers with all-cancelled orders, orders with missing delivery timestamps. Create `docs/edge-cases.md` with handling strategy for each. |

---

### Day 10 — Automated Pipeline & Scheduling

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#28** | Gourish | Build `scripts/etl_pipeline.py` — end-to-end automated script that runs ingestion → cleaning → merge → trust score → segmentation → SQL load → anomaly detection → action recommendations. Add CLI flags for partial runs. |
| **#29** | Gourish | Add pipeline logging — implement Python `logging` module throughout all `src/` modules. Write pipeline run logs to `logs/pipeline_YYYYMMDD.log` with timestamps, row counts, and error details. |
| **#30** | Hrithik | Add auto-refresh to Streamlit — implement a "Refresh Data" button that re-runs the pipeline and reloads all data. Add a timestamp indicator showing when data was last refreshed. |

---

### Day 11 — Testing & Validation

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#31** | Gourish | Write unit tests for all new modules — `tests/test_trust_score.py`, `tests/test_segmentation.py`, `tests/test_risk_signals.py`, `tests/test_anomaly_detection.py`, `tests/test_actions.py`. Target 80%+ coverage on `src/`. |
| **#32** | Himanshu | Run end-to-end data validation — execute the full pipeline from raw CSVs to final outputs. Verify row counts, check for NULL trust scores, confirm all 3,095 sellers are scored. Write results to `docs/validation-report.md`. |
| **#33** | Hrithik | UI/UX polish — apply consistent color scheme (green=Trusted, yellow=Watchlist, red=High Risk), fix chart label overlaps, add loading states, ensure responsive layout on different screen sizes. |

---

### Day 12 — Final Integration & Showcase Prep

| Issue | Assigned To | Description |
|-------|-------------|-------------|
| **#34** | Gourish | Final pipeline dry-run — run `scripts/etl_pipeline.py` from clean state. Verify all outputs generate correctly. Add a `scripts/validate_all.sh` script that runs tests + pipeline + data checks in one command. |
| **#35** | Himanshu | Compile final analytics summary — aggregate key findings: top 10 riskiest sellers, most common trust-erosion pattern, correlation between delivery delays and negative reviews. Output `docs/analytics-summary.md`. |
| **#36** | Hrithik | Final dashboard walkthrough — record a screen capture of the full dashboard flow (Overview → Scorecard → Drill-down → Actions). Prepare talking points for the showcase presentation. |

---

## Additional Coding Enhancements

These are value-add tasks to pick up if time permits or to stretch skills:

| Issue | Suggested For | Description |
|-------|---------------|-------------|
| **#E1** | Gourish | Add Parquet export alongside CSV for faster reloading of large datasets. |
| **#E2** | Hrithik | Add Plotly funnel chart showing buyer drop-off: Order Placed → Delivered → Reviewed → Positive Review. |
| **#E3** | Himanshu | Implement a simple regression model predicting next-month return rate from current-month signals. |
| **#E4** | Gourish | Add `requirements-dev.txt` with linting (ruff), formatting (black), and type-checking (mypy) tools. |
| **#E5** | Hrithik | Add a "Compare Sellers" mode in Streamlit — select 2–3 sellers and view side-by-side metrics. |
| **#E6** | Himanshu | Write a seller health report generator (PDF/HTML) for a single seller with all their metrics and charts. |

---

## File Structure (Target)

```
Brazilan/
├── app/
│   └── main.py                    # Streamlit application
├── config/
│   └── validation-rules.md
├── data/
│   ├── raw/                       # Original Olist CSVs
│   ├── processed/                 # Pipeline outputs
│   │   ├── seller_order_fact.csv
│   │   ├── seller_metrics.csv
│   │   ├── seller_segments.csv
│   │   ├── seller_risk_breakdown.csv
│   │   ├── seller_trends.csv
│   │   ├── seller_anomalies.csv
│   │   └── seller_actions.csv
│   └── trust_analytics.db         # SQLite database
├── docs/
│   ├── data-dictionary.md
│   ├── correlation-analysis.md
│   ├── edge-cases.md
│   ├── action-thresholds.md
│   ├── validation-report.md
│   └── analytics-summary.md
├── logs/
│   └── pipeline_YYYYMMDD.log
├── scripts/
│   ├── run_pipeline.py
│   └── etl_pipeline.py
├── sql/
│   ├── create_tables.sql
│   └── views.sql
├── src/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── data_quality.py
│   ├── trust_score.py
│   ├── segmentation.py
│   ├── risk_signals.py
│   ├── rolling_metrics.py
│   ├── anomaly_detection.py
│   ├── actions.py
│   ├── thresholds.py
│   ├── sql_loader.py
│   └── data_export.py
├── tests/
│   ├── test_data_quality.py
│   ├── test_pipeline.py
│   ├── test_trust_score.py
│   ├── test_segmentation.py
│   ├── test_risk_signals.py
│   ├── test_anomaly_detection.py
│   └── test_actions.py
├── requirements.txt
└── README.md
```

---

## Coding Conventions

- **Naming:** `snake_case` for files, functions, variables; `PascalCase` for classes.
- **Imports:** Group as stdlib → third-party → local. Use `from __future__ import annotations`.
- **Type hints:** All function signatures must include type hints.
- **Docstrings:** Every public function gets a one-line docstring explaining purpose.
- **No comments in code** unless explaining non-obvious business logic.
- **Git:** One PR per issue, descriptive commit messages, no secrets in code.
- **Testing:** All new `src/` modules must have corresponding `tests/test_*.py`.

---

## Dependencies

```
pandas>=2.0,<3.0
numpy>=1.24
streamlit>=1.30
plotly>=5.18
scipy>=1.11
```

---

*Last updated: Day 1 — Pipeline foundation verified (3,095 sellers, 100,010 order facts).*
