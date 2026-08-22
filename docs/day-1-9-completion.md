# Day 1–9 Delivery Checklist

This document audits the repository against the Sprint 1 plan through Day 9. The PRD and Day 8 quality work were already merged; this delivery adds the reusable pipeline needed to make the remaining work executable.

| Days | Modules | Repository evidence |
|---|---|---|
| 1–3 | 2.1–2.9 | `README.md` problem statement and `Seller-Trust-Dashboard-PRD-Olist.md` capture the product, source data, users, scope, and metrics. |
| 4–5 | 2.10–2.15 | Project structure, `.gitignore`, `requirements.txt`, source-file contract, and repeatable CSV ingestion are present. |
| 6 | 2.16–2.18 | `profile_frame` provides null/type/distinct profiling. The PRD and data dictionary define the missing-value policy. |
| 7 | 2.19–2.21 | The pipeline parses timestamps, normalises categorical text, and removes only exact duplicate rows. |
| 8 | 2.22–2.24 | `src/data_quality.py`, validation rules, and Day 8 plan implement dates, outlier flags, and timeline checks. |
| 9 | 2.25–2.27 | The seller-order fact table validates join cardinality and prevents item-level duplicate counting. Seller-level proxy metrics are engineered for later analysis. |

## Data intake

Place the five public Olist CSV files in `data/raw/` using their original filenames. Raw and processed datasets are ignored by Git because the repository contains code and documentation, not source-data copies.

```powershell
python scripts/run_pipeline.py --raw-dir data/raw --output-dir data/processed
```

The run writes `seller_order_fact.csv` and `seller_metrics.csv`. The pipeline intentionally does not assign a composite trust score yet; score weighting belongs after the Day 10 distribution/correlation analysis.
