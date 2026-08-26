"""Load processed seller data into a SQLite analytics database."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DEFAULT_DB_PATH = Path("data/trust_analytics.db")


def _create_indexes(conn) -> None:
    """Create indexes on the analytics tables."""
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_seller ON seller_order_fact(seller_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_order ON seller_order_fact(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_seller ON seller_metrics(seller_id)")
    conn.commit()


def create_tables(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Create the analytics tables and indexes if they don't already exist."""
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
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
    """)

    cursor.execute("""
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
    """)

    _create_indexes(conn)
    conn.close()


def load_to_sql(
    data_dir: Path | str = "data/processed",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, int]:
    """Load CSV files into SQLite tables and return row counts."""
    import sqlite3

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

        df = pd.read_csv(csv_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        row_counts[table_name] = len(df)

    _create_indexes(conn)
    conn.close()
    return row_counts


def get_connection(db_path: Path | str = DEFAULT_DB_PATH):
    """Return a sqlite3 connection for querying the analytics database."""
    import sqlite3

    return sqlite3.connect(str(db_path))
