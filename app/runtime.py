from __future__ import annotations

from collections.abc import Callable

from scripts.etl_pipeline import run_etl


def refresh_dashboard_data(
    pipeline: Callable[..., object] = run_etl,
    *,
    raw_dir: str = "data/raw",
    output_dir: str = "data/processed",
    db_path: str = "data/trust_analytics.db",
) -> tuple[bool, str]:
    """Run the dashboard refresh and return a user-safe result."""
    try:
        pipeline(raw_dir=raw_dir, output_dir=output_dir, db_path=db_path)
    except Exception as error:
        return False, str(error)
    return True, "Dashboard data refreshed successfully."
