import streamlit as st


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
    st.info(
        "Sortable table of all sellers (Trust Score, Return Rate, Sentiment, "
        "Response Time, Dispute Rate) with click-to-expand detail panels "
        "will be added here."
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
