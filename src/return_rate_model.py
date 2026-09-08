"""Predict a seller's next-month return rate from this month's signals (issue #43).

**On the target variable.** Olist v1 carries no returns table. There is no column
anywhere in the five raw CSVs that records a product coming back. The project's
established stand-in is `cancellation_rate_proxy` — the share of a seller's orders
that reach `order_status == "canceled"` — and this module predicts that. Every
mention of "return rate" below means that proxy. It is a real signal of orders that
did not stick, but it is not returns, and a model trained here should not be
presented as a returns model to anyone who has not read this paragraph.

**On the framing.** The task is genuinely temporal: take month *t*'s signals for a
seller and predict month *t+1*'s rate for that same seller. That shapes three
decisions that a cross-sectional model would get wrong:

1. The unit of observation is a *seller-month*, not a seller. Aggregating a seller's
   whole history into one row throws away the thing being predicted.
2. The split is by time, not at random. A random split lets the model learn from
   2018 to predict 2017, which it will never be able to do in production, and which
   inflates the score.
3. The honest baseline is persistence — "next month looks like this month" — not the
   global mean. Beating the mean is trivial; beating persistence is the question.

Usage:
    from src.return_rate_model import build_seller_month_panel, train_next_month_model
    panel = build_seller_month_panel(fact)
    result = train_next_month_model(panel)
    print(result.summary())
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

#: Orders a seller needs in a month before that month's rates are stable enough to model.
#: Below this, a single cancelled order swings the rate by 20 points or more.
MIN_ORDERS_PER_MONTH = 5

#: Share of the timeline held out for testing, taken from the end.
TEST_FRACTION = 0.25

FEATURE_COLUMNS = [
    "cancellation_rate",
    "late_delivery_rate",
    "negative_review_rate",
    "average_review_score",
    "average_delivery_delay_days",
    "total_orders",
]

#: Rates the panel carries a next-month copy of, so the same machinery can model any
#: of them. The issue asks for the return rate; the others are here because the answer
#: to "is this predictable?" turns out to depend entirely on which one you pick.
LAGGED_RATES = ["cancellation_rate", "negative_review_rate", "late_delivery_rate", "average_review_score"]

TARGET_COLUMN = "next_month_cancellation_rate"


def build_seller_month_panel(
    seller_order_fact: pd.DataFrame,
    min_orders_per_month: int = MIN_ORDERS_PER_MONTH,
) -> pd.DataFrame:
    """Aggregate the order-level fact table into one row per seller per calendar month.

    Args:
        seller_order_fact: Output of `src.pipeline.build_seller_order_fact`.
        min_orders_per_month: Months with fewer orders than this are dropped, because
            their rates are too noisy to either learn from or predict.

    Returns:
        One row per seller-month with the current month's signals and, where the
        seller also has a qualifying record for the *immediately following* calendar
        month, that month's cancellation rate in `next_month_cancellation_rate`.
        Rows with no such successor carry NaN and are dropped by the trainer.
    """
    fact = seller_order_fact.copy()
    fact["month"] = pd.to_datetime(fact["order_purchase_timestamp"], errors="coerce").dt.to_period("M")
    fact = fact.dropna(subset=["month", "seller_id"])
    fact["is_cancelled"] = fact["order_status"].eq("canceled")
    fact["is_negative_review"] = fact["review_score"].le(2)

    panel = fact.groupby(["seller_id", "month"], as_index=False).agg(
        total_orders=("order_id", "nunique"),
        cancelled_orders=("is_cancelled", "sum"),
        late_deliveries=("is_late_delivery", "sum"),
        delivered_orders=("is_late_delivery", "count"),
        negative_reviews=("is_negative_review", "sum"),
        reviewed_orders=("review_score", "count"),
        average_review_score=("review_score", "mean"),
        average_delivery_delay_days=("delivery_delay_days", "mean"),
    )
    panel = panel[panel["total_orders"] >= min_orders_per_month].copy()

    panel["cancellation_rate"] = panel["cancelled_orders"] / panel["total_orders"]
    # Denominators that can legitimately be zero: a month with nothing delivered has no
    # late-delivery rate, and a month with no reviews has no negative-review rate.
    # Leave those NaN rather than calling them zero; the trainer drops incomplete rows.
    panel["late_delivery_rate"] = np.where(
        panel["delivered_orders"] > 0, panel["late_deliveries"] / panel["delivered_orders"], np.nan
    )
    panel["negative_review_rate"] = np.where(
        panel["reviewed_orders"] > 0, panel["negative_reviews"] / panel["reviewed_orders"], np.nan
    )

    panel = panel.sort_values(["seller_id", "month"]).reset_index(drop=True)

    # Shift within seller to get the following row's rate, then keep it only where that
    # row really is the next calendar month. Without this check a seller who sells in
    # January and then not again until August would have August treated as "next month".
    grouped = panel.groupby("seller_id", sort=False)
    next_month = grouped["month"].shift(-1)
    is_consecutive = (next_month - panel["month"]).apply(lambda offset: getattr(offset, "n", None) == 1)
    for column in LAGGED_RATES:
        panel[f"next_month_{column}"] = grouped[column].shift(-1).where(is_consecutive)

    # Trailing three-month means, which carry more signal than a single noisy month.
    for column in ("cancellation_rate", "negative_review_rate", "late_delivery_rate"):
        panel[f"trailing3_{column}"] = grouped[column].transform(lambda series: series.rolling(3, min_periods=1).mean())

    return panel


@dataclass
class ModelResult:
    """Everything needed to judge the model, including what it was measured against."""

    model: LinearRegression
    target_name: str
    feature_names: list[str]
    n_train: int
    n_test: int
    train_months: tuple[str, str]
    test_months: tuple[str, str]
    r2: float
    mae: float
    baseline_persistence_r2: float
    baseline_persistence_mae: float
    baseline_mean_r2: float
    baseline_mean_mae: float
    #: Train-set mean and standard deviation per feature. Kept so predictions on new
    #: data are standardised the same way the model was fitted.
    feature_means: np.ndarray
    feature_stds: np.ndarray
    coefficients: dict[str, float] = field(default_factory=dict)

    def beats_persistence(self) -> bool:
        """Whether the model is actually worth having over 'next month = this month'."""
        return self.mae < self.baseline_persistence_mae

    def summary(self) -> str:
        lines = [
            f"Linear regression — predicting {self.target_name}",
            f"  train : {self.n_train:,} seller-months  {self.train_months[0]} to {self.train_months[1]}",
            f"  test  : {self.n_test:,} seller-months  {self.test_months[0]} to {self.test_months[1]}",
            "",
            f"  {'model':28s} R2 {self.r2:+.4f}   MAE {self.mae:.4f}",
            f"  {'baseline: persistence':28s} R2 {self.baseline_persistence_r2:+.4f}   "
            f"MAE {self.baseline_persistence_mae:.4f}",
            f"  {'baseline: train mean':28s} R2 {self.baseline_mean_r2:+.4f}   MAE {self.baseline_mean_mae:.4f}",
            "",
            "  coefficients (standardised inputs, so magnitudes are comparable):",
        ]
        for name, value in sorted(self.coefficients.items(), key=lambda kv: -abs(kv[1])):
            lines.append(f"      {name:32s} {value:+.5f}")
        verdict = "beats persistence" if self.beats_persistence() else "does NOT beat persistence"
        lines += ["", f"  verdict: {verdict} on MAE"]
        return "\n".join(lines)


def train_next_month_model(
    panel: pd.DataFrame,
    target_column: str = TARGET_COLUMN,
    feature_columns: list[str] | None = None,
    test_fraction: float = TEST_FRACTION,
) -> ModelResult:
    """Fit a linear regression predicting next month's rate, split by time.

    Args:
        panel: Output of `build_seller_month_panel`.
        target_column: Which `next_month_*` column to predict.
        feature_columns: Current-month signals to use. Defaults to `FEATURE_COLUMNS`.
        test_fraction: Share of the *calendar timeline* held out from the end.

    Raises:
        ValueError: If there is not enough usable history on both sides of the split.
    """
    features = list(feature_columns or FEATURE_COLUMNS)
    if target_column not in panel.columns:
        raise ValueError(f"Panel has no column {target_column!r}; expected one of {LAGGED_RATES}.")
    persistence_column = target_column.removeprefix("next_month_")
    usable = panel.dropna(subset=[*features, target_column]).copy()
    if usable.empty:
        raise ValueError("No seller-months have both a complete feature set and a next-month target.")

    months = sorted(usable["month"].unique())
    if len(months) < 4:
        raise ValueError(f"Need at least 4 distinct months to split by time, found {len(months)}.")
    cutoff = months[int(len(months) * (1 - test_fraction))]

    train = usable[usable["month"] < cutoff]
    test = usable[usable["month"] >= cutoff]
    if train.empty or test.empty:
        raise ValueError("Time-based split left one side empty; widen the data or lower test_fraction.")

    x_train, y_train = train[features].to_numpy(dtype=float), train[target_column].to_numpy(dtype=float)
    x_test, y_test = test[features].to_numpy(dtype=float), test[target_column].to_numpy(dtype=float)

    # Standardise on train statistics only — computing them over the whole panel would
    # leak test-set distribution into training.
    means = x_train.mean(axis=0)
    stds = x_train.std(axis=0)
    stds[stds == 0] = 1.0

    model = LinearRegression()
    model.fit((x_train - means) / stds, y_train)
    predictions = model.predict((x_test - means) / stds)

    # Persistence: assume next month equals this month. This is the bar to clear.
    persistence = test[persistence_column].to_numpy(dtype=float)
    train_mean = np.full_like(y_test, float(y_train.mean()))

    return ModelResult(
        model=model,
        target_name=target_column,
        feature_names=features,
        n_train=len(train),
        n_test=len(test),
        train_months=(str(train["month"].min()), str(train["month"].max())),
        test_months=(str(test["month"].min()), str(test["month"].max())),
        r2=float(r2_score(y_test, predictions)),
        mae=float(mean_absolute_error(y_test, predictions)),
        baseline_persistence_r2=float(r2_score(y_test, persistence)),
        baseline_persistence_mae=float(mean_absolute_error(y_test, persistence)),
        baseline_mean_r2=float(r2_score(y_test, train_mean)),
        baseline_mean_mae=float(mean_absolute_error(y_test, train_mean)),
        feature_means=means,
        feature_stds=stds,
        coefficients=dict(zip(features, (float(c) for c in model.coef_), strict=True)),
    )


def predict_next_month(result: ModelResult, panel_rows: pd.DataFrame) -> np.ndarray:
    """Predict next month's rate for seller-months already shaped by `build_seller_month_panel`."""
    missing = [column for column in result.feature_names if column not in panel_rows.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {', '.join(missing)}")
    features = panel_rows[result.feature_names].to_numpy(dtype=float)
    # Same standardisation as training, using the stored train-set statistics.
    return result.model.predict((features - result.feature_means) / result.feature_stds)
