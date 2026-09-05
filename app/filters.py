from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.sql_loader import DEFAULT_DB_PATH
from src.trust_score import calculate_trust_score

RISK_TIERS = ["All", "Reliable", "Inconsistent", "Return-Prone", "High-Risk"]


def _connect(db_path: str | Path) -> sqlite3.Connection:
    db_file = Path(db_path)
    if not db_file.is_file():
        raise FileNotFoundError(f"SQLite database not found: {db_file}")
    return sqlite3.connect(str(db_file))


def assign_risk_tier(metrics: pd.DataFrame) -> pd.DataFrame:
    prepared = metrics.copy()
    prepared["eligible_for_risk_score"] = prepared["eligible_for_risk_score"].astype(bool)
    scored = calculate_trust_score(prepared)
    scored["risk_tier"] = pd.cut(
        scored["trust_score"],
        bins=[-0.01, 45, 60, 75, 100],
        labels=["High-Risk", "Return-Prone", "Inconsistent", "Reliable"],
    ).astype("string")
    scored.loc[scored["trust_score"].isna(), "risk_tier"] = "Insufficient Data"
    return scored


def get_category_options(db_path: str | Path = DEFAULT_DB_PATH) -> list[str]:
    query = """
        SELECT DISTINCT product_category_name
        FROM seller_order_fact
        WHERE product_category_name IS NOT NULL
        ORDER BY product_category_name
    """
    with _connect(db_path) as conn:
        categories = pd.read_sql_query(query, conn)["product_category_name"].tolist()
    return ["All"] + categories


def query_seller_metrics(
    seller_search: str = "",
    risk_tier: str = "All",
    category: str = "All",
    db_path: str | Path = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    where_clauses: list[str] = []
    params: list[str] = []

    if seller_search.strip():
        where_clauses.append("m.seller_id LIKE ?")
        params.append(f"%{seller_search.strip()}%")

    if category != "All":
        where_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM seller_order_fact f
                WHERE f.seller_id = m.seller_id
                AND f.product_category_name = ?
            )
            """
        )
        params.append(category)

    query = "SELECT m.* FROM seller_metrics m"
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY m.seller_id"

    with _connect(db_path) as conn:
        metrics = pd.read_sql_query(query, conn, params=params)

    filtered = assign_risk_tier(metrics)
    if risk_tier != "All":
        filtered = filtered[filtered["risk_tier"] == risk_tier]
    return filtered
