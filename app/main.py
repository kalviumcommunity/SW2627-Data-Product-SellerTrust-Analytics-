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

overview_tab, scorecard_tab, alerts_tab = st.tabs(
    ["Overview", "Seller Scorecard", "Risk Alerts"]
)

with overview_tab:
    st.subheader("Overview")
    st.info("Marketplace-level trust KPIs and trend summaries will be added here.")

with scorecard_tab:
    st.subheader("Seller Scorecard")
    st.info("Seller ranking, metric breakdowns, and drill-down details will be added here.")

with alerts_tab:
    st.subheader("Risk Alerts")
    st.info("High-risk seller flags and recommended actions will be added here.")
