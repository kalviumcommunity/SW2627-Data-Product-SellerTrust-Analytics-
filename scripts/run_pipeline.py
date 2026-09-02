"""Command-line entry point for the Olist pipeline."""

import argparse

from src.pipeline import run_pipeline


parser = argparse.ArgumentParser(description="Build Seller Trust Analytics processed data.")
parser.add_argument("--raw-dir", default="data/raw", help="Directory containing the five Olist CSVs.")
parser.add_argument("--output-dir", default="data/processed", help="Directory for generated CSV outputs.")
parser.add_argument(
    "--full-refresh",
    action="store_true",
    help="Run full pipeline: ingest, clean, score, detect anomalies, generate actions, load SQL.",
)
parser.add_argument(
    "--db-path",
    default="data/trust_analytics.db",
    help="Path for the SQLite database (used with --full-refresh).",
)
args = parser.parse_args()

if args.full_refresh:
    from src.data_export import full_refresh

    print("Running full pipeline refresh...")
    counts = full_refresh(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        db_path=args.db_path,
    )
    for name, count in counts.items():
        print(f"  {name}: {count:,} rows")
    print("Full refresh complete.")
else:
    outputs = run_pipeline(args.raw_dir, args.output_dir)
    for name, frame in outputs.items():
        print(f"Wrote {name}: {len(frame):,} rows")
