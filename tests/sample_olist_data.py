from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_sample_raw_files(raw_dir: Path) -> None:
    """Write a tiny Olist-shaped raw dataset for pipeline integration tests."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "order_id": ["o1", "o2"],
            "customer_id": ["c1", "c2"],
            "order_status": ["delivered", "canceled"],
            "order_purchase_timestamp": ["2024-01-01", "2024-01-03"],
            "order_approved_at": ["2024-01-01", "2024-01-03"],
            "order_delivered_carrier_date": ["2024-01-02", None],
            "order_delivered_customer_date": ["2024-01-05", None],
            "order_estimated_delivery_date": ["2024-01-04", "2024-01-10"],
        }
    ).to_csv(raw_dir / "olist_orders_dataset.csv", index=False)
    pd.DataFrame(
        {
            "order_id": ["o1", "o2"],
            "product_id": ["p1", "p2"],
            "seller_id": ["s1", "s1"],
            "price": [100.0, 50.0],
            "freight_value": [10.0, 5.0],
        }
    ).to_csv(raw_dir / "olist_order_items_dataset.csv", index=False)
    pd.DataFrame(
        {
            "review_id": ["r1", "r2"],
            "order_id": ["o1", "o2"],
            "review_score": [5, 2],
            "review_creation_date": ["2024-01-06", "2024-01-11"],
            "review_answer_timestamp": ["2024-01-07", "2024-01-12"],
        }
    ).to_csv(raw_dir / "olist_order_reviews_dataset.csv", index=False)
    pd.DataFrame(
        {
            "seller_id": ["s1"],
            "seller_zip_code_prefix": [12345],
            "seller_city": ["sao paulo"],
            "seller_state": ["sp"],
        }
    ).to_csv(raw_dir / "olist_sellers_dataset.csv", index=False)
    pd.DataFrame(
        {
            "product_id": ["p1", "p2"],
            "product_category_name": ["books", "electronics"],
        }
    ).to_csv(raw_dir / "olist_products_dataset.csv", index=False)
