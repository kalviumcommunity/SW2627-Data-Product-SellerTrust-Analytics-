# End-to-End Data Validation Report

## Pipeline Execution Summary
- Date: 2026-09-06
- Raw Data Source: Olist v1 CSVs (5 files) - MISSING
- Pipeline Status: FAILED

## Error Details
The pipeline failed to execute due to missing raw data files.
Error: FileNotFoundError: Missing required raw files: olist_orders_dataset.csv, olist_order_items_dataset.csv, olist_order_reviews_dataset.csv, olist_sellers_dataset.csv, olist_products_dataset.csv

## Data Quality Checks
Could not be performed due to pipeline failure.

## Overall Validation Result
VALIDATION FAILED - Pipeline could not execute because raw Olist dataset is not present in data/raw/. Please download the five required CSV files from https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce and place them in data/raw/ before re-running.
