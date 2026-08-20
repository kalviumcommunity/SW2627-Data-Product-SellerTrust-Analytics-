# Seller Trust Analytics

## Problem statement

An e-commerce marketplace tracks seller performance, return requests, and customer review sentiment, but no operational dashboard identifies which seller behaviours consistently reduce customer trust over time.

## Day 8 progress — Modules 2.22–2.24

The initial data-quality foundation is ready:

- Date/time transformations for delivery lateness and monthly analysis
- IQR-based outlier flags that preserve unusual records for investigation
- Order-timeline validation rules and automated tests

Run the checks from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

See [the Day 8 plan](docs/day-8-data-quality-plan.md) and [validation rules](config/validation-rules.md) for the business definitions.
