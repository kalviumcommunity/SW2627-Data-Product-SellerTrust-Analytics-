# Seller Trust Analytics

A data-driven dashboard that identifies which e-commerce sellers are eroding customer trust — before the pattern becomes a crisis.

---

## The Problem

Olist tracks seller performance, order status, and customer reviews across separate tables. No single view connects them, so a seller whose behaviour is slowly damaging customer trust — late deliveries, product-mismatch complaints, poor reviews — doesn't get flagged until it shows up as a pattern of bad reviews. By then, customers have already had the bad experience.

## The Solution

This project builds an end-to-end analytics pipeline and interactive dashboard that combines delivery performance, order outcomes, and review sentiment per seller into a single trust-risk score. Sellers are segmented into tiers and assigned recommended actions — so the ops team can intervene early, not after the fact.

---

## What the Dashboard Shows

| Section | What It Does |
|---------|--------------|
| **Trust Overview** | Marketplace-wide KPIs — avg trust score, return rate, negative sentiment %, at-risk seller count |
| **Trust vs. Behaviour Signals** | Scatter plots, correlation heatmaps, and cohort comparisons showing which behaviours erode trust |
| **Seller Scorecard** | Sortable table of all sellers with drill-down metrics — searchable by seller ID, risk tier, and product category |
| **Behaviour Segments** | Portfolio view grouping sellers into Reliable, Inconsistent, Return-Prone, and High-Risk tiers |
| **Trust-Risk Actions** | Recommended actions (Escalate / Coach / Monitor) with supporting evidence per flagged seller |

---

## How It Works

1. **Ingest** — Raw Olist CSVs (orders, items, reviews, sellers, products) are loaded and cleaned
2. **Merge** — Data is joined into a seller-order fact table with delivery, review, and cancellation signals
3. **Score** — Each seller gets a composite trust score (0–100) combining delivery performance, review quality, cancellation rate, and negative review rate
4. **Detect** — Anomaly detection (IQR + Z-score) flags sellers with sudden behaviour spikes
5. **Recommend** — An action engine assigns Escalate / Coach / Monitor based on trust score and anomaly count
6. **Visualize** — Everything is displayed in an interactive Streamlit dashboard with Plotly charts

---

## Tech Stack

- **Python** — Pandas, NumPy, SciPy for data processing and statistical analysis
- **SQLite** — Analytics database with indexed tables and pre-built SQL views
- **Streamlit** — Interactive dashboard with sidebar filters and tabbed navigation
- **Plotly** — Scatter plots, heatmaps, time-series charts, and performance decay visualizations
- **GitHub Actions** — CI/CD for automated testing

---

## Getting Started

### Prerequisites

- Python 3.11+
- Download the [Olist Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place these 5 CSVs in `data/raw/`:
  - `olist_orders_dataset.csv`
  - `olist_order_items_dataset.csv`
  - `olist_order_reviews_dataset.csv`
  - `olist_sellers_dataset.csv`
  - `olist_products_dataset.csv`

### Installation

```bash
pip install -r requirements.txt
```

### Run the Pipeline

```bash
python scripts/run_pipeline.py --raw-dir data/raw --output-dir data/processed
```

### Load Data into SQLite

```python
from src.sql_loader import load_to_sql
load_to_sql("data/processed", "data/trust_analytics.db")
```

### Launch the Dashboard

```bash
python -m streamlit run app/main.py
```

The dashboard opens at `http://localhost:8501`.

---

## Project Structure

```
Brazilan/
├── app/                    # Streamlit dashboard
│   ├── main.py             # App entry point and tab routing
│   ├── overview.py         # Trust Overview KPI cards
│   ├── filters.py          # Sidebar filters and SQLite queries
│   └── signals.py          # Behaviour signal charts (Plotly)
├── src/                    # Core analytics modules
│   ├── pipeline.py         # Data ingestion, cleaning, merge
│   ├── data_quality.py     # Date parsing, validation, outlier flags
│   ├── trust_score.py      # Composite trust score engine (0–100)
│   ├── thresholds.py       # Statistical threshold derivation
│   ├── sql_loader.py       # SQLite database loader
│   ├── anomaly_detection.py# IQR + Z-score anomaly detection
│   └── actions.py          # Action recommendation engine
├── sql/                    # SQL views for analytics
├── tests/                  # Unit tests
├── scripts/                # CLI entry points
├── data/
│   ├── raw/                # Original Olist CSVs
│   └── processed/          # Pipeline outputs
└── docs/                   # Data dictionary, analysis reports
```

---

## Trust Score Formula

The composite trust score (0–100) weights four signals:

| Signal | Weight | Source |
|--------|--------|--------|
| Delivery Performance | 30% | `(1 - late_delivery_rate) × 100` |
| Review Quality | 30% | `(avg_review - 1) / 4 × 100` |
| Cancellation Score | 20% | `(1 - cancellation_rate) × 100` |
| Negative Review Score | 20% | `(1 - negative_review_rate) × 100` |

Sellers with fewer than 5 orders are excluded from scoring for statistical stability.

---

## License

Built for educational purposes using the [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
