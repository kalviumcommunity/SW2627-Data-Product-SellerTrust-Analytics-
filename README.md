# Seller Trust Analytics

## Problem statement

An e-commerce marketplace tracks seller performance, return requests, and customer review sentiment, but no operational dashboard identifies which seller behaviours consistently reduce customer trust over time.

## Sprint 1 progress — Days 1–9

The initial data-quality foundation is ready:

- PRD, wireframe mapping, dataset contract, and data dictionary
- Repeatable Olist CSV ingestion, profiling, cleaning, and merge workflow
- Date/time transformations, IQR outlier flags, and timeline validation rules
- Seller-order fact data and PRD-aligned seller proxy metrics

Run the checks from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

To run the pipeline once the five Olist v1 CSVs are placed in `data/raw/`:

```powershell
python scripts/run_pipeline.py --raw-dir data/raw --output-dir data/processed
```

See the [Day 1–9 delivery checklist](docs/day-1-9-completion.md), [data dictionary](docs/data-dictionary.md), [Day 8 plan](docs/day-8-data-quality-plan.md), and [validation rules](config/validation-rules.md).
