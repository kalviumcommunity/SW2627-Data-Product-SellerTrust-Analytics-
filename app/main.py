import streamlit as st

from app.filters import RISK_TIERS, get_category_options, query_seller_metrics


st.set_page_config(
    page_title="Seller Trust Analytics Dashboard",
    layout="wide",
)


st.title("Seller Trust Analytics Dashboard")

with st.sidebar:
    st.header("Seller Trust Analytics")
    st.write(
        "Explore seller trust signals using delivery performance, review scores, "
        "cancellation proxies, and risk indicators from the Olist e-commerce data."
    )
    st.caption(
        "Use the dashboard tabs to move from marketplace overview to seller-level risk alerts."
    )
    st.divider()
    seller_search = st.text_input("Seller search", placeholder="Search seller_id")
    selected_risk_tier = st.selectbox("Risk tier", RISK_TIERS)
    try:
        category_options = get_category_options()
    except FileNotFoundError:
        category_options = ["All"]
        st.warning("Load data/trust_analytics.db to enable category filtering.")
    selected_category = st.selectbox("Category", category_options)

try:
    filtered_seller_metrics = query_seller_metrics(
        seller_search=seller_search,
        risk_tier=selected_risk_tier,
        category=selected_category,
    )
except FileNotFoundError:
    filtered_seller_metrics = None
except (KeyError, TypeError, ValueError) as error:
    filtered_seller_metrics = None
    st.error(f"Unable to query seller metrics from SQLite: {error}")

overview_tab, signals_tab, scorecard_tab, segments_tab, actions_tab = st.tabs(
    [
        "Trust Overview",
        "Trust vs. Behaviour Signals",
        "Seller Scorecard",
        "Behaviour Segments",
        "Trust-Risk Actions",
    ]
)

with overview_tab:
    st.subheader("Trust Overview")
    st.info(
        "Marketplace-wide KPI cards (Avg Trust Score, Return Rate %, "
        "Negative Sentiment %, At-Risk Sellers), trust-score distribution histogram, "
        "and Top Trust-Eroding Behaviours ranking chart will be added here."
    )

with signals_tab:
    st.subheader("Trust vs. Behaviour Signals")
    st.info(
        "Cohort comparison table (high-trust vs low-trust sellers), "
        "trust-score trend line, return-rate-vs-trust-score scatter plot, "
        "and behaviour-correlation bar chart will be added here."
    )

with scorecard_tab:
    st.subheader("Seller Scorecard")
    if filtered_seller_metrics is None:
        st.warning(
            "Load data/trust_analytics.db to use sidebar filters and view seller metrics."
        )
    elif filtered_seller_metrics.empty:
        st.info("No sellers match the selected filters.")
    else:
        st.caption(
            f"{len(filtered_seller_metrics):,} sellers match the selected filters."
        )
        st.dataframe(
            filtered_seller_metrics[
                [
                    "seller_id",
                    "risk_tier",
                    "trust_score",
                    "total_orders",
                    "cancellation_rate_proxy",
                    "negative_review_rate",
                    "late_delivery_rate",
                    "average_review_score",
                ]
            ],
            hide_index=True,
            use_container_width=True,
        )

with segments_tab:
    st.subheader("Behaviour Segments")
    st.info(
        "Portfolio view grouping sellers into 4 tiers "
        "(Reliable / Inconsistent / Return-Prone / High-Risk) with "
        "a stacked bar showing tier composition will be added here."
    )

with actions_tab:
    st.subheader("Trust-Risk Actions")
    st.info(
        "Action cards per flagged seller with recommended tier "
        "(Escalate / Coach / Monitor) and supporting evidence "
        "will be added here."
    )
