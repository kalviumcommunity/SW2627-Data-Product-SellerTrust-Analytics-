"""Command-line entry point for the Day 1–9 Olist pipeline."""

import argparse

from src.pipeline import run_pipeline


parser = argparse.ArgumentParser(description="Build Seller Trust Analytics processed data.")
parser.add_argument("--raw-dir", default="data/raw", help="Directory containing the five Olist CSVs.")
parser.add_argument("--output-dir", default="data/processed", help="Directory for generated CSV outputs.")
args = parser.parse_args()

outputs = run_pipeline(args.raw_dir, args.output_dir)
for name, frame in outputs.items():
    print(f"Wrote {name}: {len(frame):,} rows")
