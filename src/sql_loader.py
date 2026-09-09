"""Load processed seller data into a SQLite analytics database."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from src.logging_config import get_pipeline_logger
from src.pipeline_cache import load_cached_csv

DEFAULT_DB_PATH = Path("data/trust_analytics.db")
DEFAULT_VIEWS_PATH = Path(__file__).resolve().parent.parent / "sql" / "views.sql"

#: Matches the view names declared in sql/views.sql, so a re-run can drop exactly the
#: views that file owns rather than every view in the database.
_CREATE_VIEW = re.compile(r"CREATE\s+VIEW\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][\w]*)", re.IGNORECASE)
log = get_pipeline_logger("sql_loader")


def view_names(views_path: Path | str = DEFAULT_VIEWS_PATH) -> list[str]:
    """Names of the views declared in the SQL file, in declaration order."""
    return _CREATE_VIEW.findall(Path(views_path).read_text(encoding="utf-8"))


def apply_views(
    db_path: Path | str = DEFAULT_DB_PATH,
    views_path: Path | str = DEFAULT_VIEWS_PATH,
) -> list[str]:
    """Create the analytics views defined in sql/views.sql.

    Existing copies are dropped first. `views.sql` uses bare `CREATE VIEW`, so a second
    run would otherwise fail; dropping also means an edited definition actually takes
    effect, which `CREATE VIEW IF NOT EXISTS` would silently skip.

    Returns:
        The view names created, in declaration order.

    Raises:
        FileNotFoundError: If the SQL file is missing.
    """
    sql_path = Path(views_path)
    if not sql_path.is_file():
        raise FileNotFoundError(f"Missing SQL views file: {sql_path}")

    names = view_names(sql_path)
    conn = sqlite3.connect(str(db_path))
    try:
        for name in names:
            conn.execute(f"DROP VIEW IF EXISTS {name}")
        conn.executescript(sql_path.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    return names


def _create_indexes(conn) -> None:
    """Create indexes on the analytics tables."""
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_seller ON seller_order_fact(seller_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_order ON seller_order_fact(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_seller ON seller_metrics(seller_id)")
    conn.commit()


def create_tables(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Create the analytics tables and indexes if they don't already exist."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS seller_order_fact (
            order_id TEXT NOT NULL,
            seller_id TEXT NOT NULL,
            item_count INTEGER,
            item_value REAL,
            freight_value REAL,
            product_category_name TEXT,
            customer_id TEXT,
            order_status TEXT,
            order_purchase_timestamp TEXT,
            order_approved_at TEXT,
            order_delivered_carrier_date TEXT,
            order_delivered_customer_date TEXT,
            order_estimated_delivery_date TEXT,
            delivery_delay_days REAL,
            is_late_delivery INTEGER,
            order_age_days REAL,
            purchase_month TEXT,
            seller_zip_code_prefix INTEGER,
            seller_city TEXT,
            seller_state TEXT,
            review_score REAL,
            review_count REAL,
            response_time_hours REAL,
            sentiment_bucket TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS seller_metrics (
            seller_id TEXT NOT NULL,
            total_orders INTEGER,
            cancelled_orders INTEGER,
            late_delivery_rate REAL,
            average_delivery_delay_days REAL,
            average_review_score REAL,
            negative_review_rate REAL,
            average_response_time_hours REAL,
            cancellation_rate_proxy REAL,
            eligible_for_risk_score INTEGER
        )
    """
    )

    _create_indexes(conn)
    conn.close()


def load_to_sql(
    data_dir: Path | str = "data/processed",
    db_path: Path | str = DEFAULT_DB_PATH,
    views_path: Path | str | None = DEFAULT_VIEWS_PATH,
) -> dict[str, int]:
    """Load CSV files into SQLite tables, rebuild the analytics views, return row counts.

    Views are rebuilt after the tables load, because `to_sql(if_exists="replace")` drops
    and recreates each table underneath them. Pass `views_path=None` to load data only.
    """
    data_path = Path(data_dir)
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_file))
    row_counts: dict[str, int] = {}

    for table_name in ("seller_order_fact", "seller_metrics"):
        csv_path = data_path / f"{table_name}.csv"
        if not csv_path.is_file():
            conn.close()
            raise FileNotFoundError(f"Missing CSV: {csv_path}")

        df = load_cached_csv(csv_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        row_counts[table_name] = len(df)

    _create_indexes(conn)
    conn.close()

    if views_path is not None:
        apply_views(db_file, views_path)
    log.info(
        "Loaded SQL tables into %s: %s",
        db_file,
        ", ".join(f"{name}={count} rows" for name, count in row_counts.items()),
    )
    return row_counts


def get_connection(db_path: Path | str = DEFAULT_DB_PATH):
    """Return a sqlite3 connection for querying the analytics database."""
    return sqlite3.connect(str(db_path))
