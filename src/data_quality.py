"""Day 8 data-quality utilities: dates, outliers, and business-rule validation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

ORDER_DATE_COLUMNS = (
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
)


@dataclass(frozen=True)
class ValidationResult:
    """A named validation result suitable for logs, tests, or a dashboard alert."""

    rule: str
    passed: bool
    failed_rows: int
    message: str


def parse_order_datetimes(orders: pd.DataFrame) -> pd.DataFrame:
    """Parse known Olist timestamp columns without turning bad values into crashes."""
    parsed = orders.copy()
    for column in ORDER_DATE_COLUMNS:
        if column in parsed.columns:
            parsed[column] = pd.to_datetime(parsed[column], errors="coerce")
    return parsed


def add_delivery_features(orders: pd.DataFrame) -> pd.DataFrame:
    """Add delivery lateness and lifecycle durations used in seller-risk analysis.

    Positive ``delivery_delay_days`` means a delivery occurred after the estimate.
    Missing delivery timestamps remain missing rather than being imputed as on time.
    """
    enriched = parse_order_datetimes(orders)
    required = {"order_purchase_timestamp", "order_estimated_delivery_date"}
    missing = required.difference(enriched.columns)
    if missing:
        raise ValueError(f"Missing required order date columns: {sorted(missing)}")

    delivered = enriched.get("order_delivered_customer_date")
    if delivered is None:
        delivered = pd.Series(pd.NaT, index=enriched.index, dtype="datetime64[ns]")

    enriched["delivery_delay_days"] = (
        delivered - enriched["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86_400
    enriched["is_late_delivery"] = enriched["delivery_delay_days"].gt(0).astype("boolean")
    enriched["order_age_days"] = (
        enriched["order_estimated_delivery_date"] - enriched["order_purchase_timestamp"]
    ).dt.total_seconds() / 86_400
    enriched["purchase_month"] = enriched["order_purchase_timestamp"].dt.to_period("M").astype("string")
    return enriched


def flag_iqr_outliers(frame: pd.DataFrame, column: str, *, multiplier: float = 1.5) -> pd.DataFrame:
    """Flag, but do not remove, IQR outliers in a numeric column.

    Flags preserve unusual yet valid seller behaviour for later investigation.
    """
    if column not in frame.columns:
        raise ValueError(f"Column not found: {column}")
    if multiplier <= 0:
        raise ValueError("multiplier must be positive")

    flagged = frame.copy()
    values = pd.to_numeric(flagged[column], errors="coerce")
    q1, q3 = values.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower, upper = q1 - multiplier * iqr, q3 + multiplier * iqr
    outlier = (values.lt(lower) | values.gt(upper)).astype("boolean")
    outlier.loc[values.isna()] = pd.NA
    flagged[f"{column}_outlier"] = outlier
    return flagged


def validate_order_timeline(orders: pd.DataFrame) -> list[ValidationResult]:
    """Check temporal relationships that must hold before downstream analysis."""
    parsed = parse_order_datetimes(orders)

    def invalid(later: str, earlier: str) -> int:
        if later not in parsed or earlier not in parsed:
            return 0
        comparable = parsed[later].notna() & parsed[earlier].notna()
        return int((parsed.loc[comparable, later] < parsed.loc[comparable, earlier]).sum())

    rules = [
        ("approval_after_purchase", "order_approved_at", "order_purchase_timestamp"),
        ("carrier_after_purchase", "order_delivered_carrier_date", "order_purchase_timestamp"),
        ("delivery_after_purchase", "order_delivered_customer_date", "order_purchase_timestamp"),
        ("delivery_after_carrier", "order_delivered_customer_date", "order_delivered_carrier_date"),
    ]
    return [
        ValidationResult(
            rule=name,
            passed=(failed := invalid(later, earlier)) == 0,
            failed_rows=failed,
            message=f"{later} must not precede {earlier}",
        )
        for name, later, earlier in rules
    ]


def require_valid_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Enrich orders and fail fast when a timeline validation rule is violated."""
    results = validate_order_timeline(orders)
    failed = [result for result in results if not result.passed]
    if failed:
        details = "; ".join(f"{item.rule}: {item.failed_rows}" for item in failed)
        raise ValueError(f"Order timeline validation failed ({details})")
    return add_delivery_features(orders)
