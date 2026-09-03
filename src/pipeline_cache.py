"""Pipeline performance profiling and caching utilities."""

from __future__ import annotations

import cProfile
import io
import pstats
from functools import lru_cache
from pathlib import Path

import pandas as pd


def load_cached_csv(csv_path: Path, use_parquet_cache: bool = True) -> pd.DataFrame:
    """Load a CSV with optional Parquet caching for faster reload.

    On first load, reads CSV and writes a .parquet sibling. On subsequent
    loads, reads Parquet if it exists and is newer than the CSV.
    """
    if use_parquet_cache:
        parquet_path = csv_path.with_suffix(".parquet")
        if parquet_path.is_file() and parquet_path.stat().st_mtime >= csv_path.stat().st_mtime:
            return pd.read_parquet(parquet_path)

    df = pd.read_csv(csv_path)

    if use_parquet_cache:
        try:
            df.to_parquet(csv_path.with_suffix(".parquet"), index=False)
        except Exception:
            pass  # fallback silently if pyarrow isn't installed

    return df


def profile_pipeline(raw_dir: str, output_dir: str, top_n: int = 15) -> str:
    """Run run_pipeline under cProfile and return a formatted stats summary."""
    from src.pipeline import run_pipeline

    profiler = cProfile.Profile()
    profiler.enable()
    run_pipeline(raw_dir, output_dir)
    profiler.disable()

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats(top_n)
    return stream.getvalue()


@lru_cache(maxsize=1)
def _cached_run_pipeline(raw_dir: str, output_dir: str) -> dict[str, pd.DataFrame]:
    """LRU-cached wrapper around run_pipeline. Call with same args to reuse."""
    from src.pipeline import run_pipeline

    return run_pipeline(raw_dir, output_dir)


def run_pipeline_cached(raw_dir: str | Path, output_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Run pipeline with LRU caching. Returns cached result if args unchanged."""
    return _cached_run_pipeline(str(raw_dir), str(output_dir))
