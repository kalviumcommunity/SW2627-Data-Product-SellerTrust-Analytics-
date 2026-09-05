import streamlit as st

from app.actions import build_action_cards, format_evidence_bullets
from app.filters import RISK_TIERS, get_category_options, query_seller_metrics
from app.overview import build_overview_kpis, load_seller_metrics
from app.scorecard import add_alert_badges, build_anomaly_detail_rows
from app.segments import build_segment_composition_chart, build_segment_summary
from app.signals import (
    build_cohort_comparison,
    build_correlation_heatmap,
    build_monthly_sentiment_bar,
    build_performance_decay_chart,
    build_return_rate_scatter,
    build_trust_score_trend,
    load_seller_order_fact,
    prepare_monthly_seller_metrics,
    prepare_signal_metrics,
)

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
    st.caption("Use the dashboard tabs to move from marketplace overview to seller-level risk alerts.")
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
    try:
        seller_metrics = load_seller_metrics()
        overview_kpis = build_overview_kpis(seller_metrics)
    except FileNotFoundError:
        st.warning("Generate data/processed/seller_metrics.csv to populate the Trust Overview cards.")
    except (KeyError, TypeError, ValueError) as error:
        st.error(f"Unable to build Trust Overview KPIs from seller_metrics.csv: {error}")
    else:
        card_1, card_2, card_3, card_4 = st.columns(4)
        card_1.metric("Avg Trust Score", f"{overview_kpis['avg_trust_score']:.1f}")
        card_2.metric("Return Rate %", f"{overview_kpis['return_rate_pct']:.1f}%")
        card_3.metric(
            "Negative Sentiment %",
            f"{overview_kpis['negative_sentiment_pct']:.1f}%",
        )
        card_4.metric("At-Risk Sellers", f"{overview_kpis['at_risk_sellers_count']:,}")

        st.caption(
            "Return Rate uses the PRD's cancellation-rate proxy. Negative Sentiment uses the share of 1-2 star reviews."
        )
        st.dataframe(
            seller_metrics.head(10),
            hide_index=True,
            use_container_width=True,
        )

with signals_tab:
    st.subheader("Trust vs. Behaviour Signals")
    if filtered_seller_metrics is None:
        st.warning("Load data/trust_analytics.db to compare seller behaviour signals.")
    else:
        signal_metrics = prepare_signal_metrics(filtered_seller_metrics)
        if signal_metrics.empty:
            st.info("No eligible sellers match the current filters.")
        else:
            st.caption(
                "Return Rate uses the PRD's cancellation proxy. "
                "Use this section to compare trust score against delivery, review, "
                "and cancellation behaviour."
            )
            scatter_col, heatmap_col = st.columns(2)
            with scatter_col:
                st.plotly_chart(
                    build_return_rate_scatter(signal_metrics),
                    use_container_width=True,
                )
            with heatmap_col:
                st.plotly_chart(
                    build_correlation_heatmap(signal_metrics),
                    use_container_width=True,
                )

            st.markdown("#### High-Trust vs Low-Trust Cohorts")
            st.dataframe(
                build_cohort_comparison(signal_metrics),
                hide_index=True,
                use_container_width=True,
            )

            try:
                order_fact = load_seller_order_fact(signal_metrics["seller_id"])
            except FileNotFoundError:
                order_fact = None
                st.warning("Load data/trust_analytics.db to show seller performance trends.")

            if order_fact is not None:
                monthly_metrics = prepare_monthly_seller_metrics(order_fact)
                if monthly_metrics.empty:
                    st.info("No monthly seller history is available for trend visuals.")
                else:
                    st.markdown("#### Seller Performance Trends")
                    st.plotly_chart(
                        build_trust_score_trend(monthly_metrics),
                        use_container_width=True,
                    )
                    sentiment_col, decay_col = st.columns(2)
                    with sentiment_col:
                        st.plotly_chart(
                            build_monthly_sentiment_bar(order_fact),
                            use_container_width=True,
                        )
                    with decay_col:
                        st.plotly_chart(
                            build_performance_decay_chart(monthly_metrics),
                            use_container_width=True,
                        )

with scorecard_tab:
    st.subheader("Seller Scorecard")
    if filtered_seller_metrics is None:
        st.warning("Load data/trust_analytics.db to use sidebar filters and view seller metrics.")
    elif filtered_seller_metrics.empty:
        st.info("No sellers match the selected filters.")
    else:
        scorecard_metrics = add_alert_badges(filtered_seller_metrics)
        st.caption(f"{len(scorecard_metrics):,} sellers match the selected filters.")
        st.dataframe(
            scorecard_metrics[
                [
                    "alert_badge",
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
        try:
            scorecard_order_fact = load_seller_order_fact(scorecard_metrics["seller_id"])
        except FileNotFoundError:
            scorecard_order_fact = None
        anomaly_details = build_anomaly_detail_rows(
            scorecard_metrics,
            scorecard_order_fact,
        )
        if anomaly_details.empty:
            st.success("No anomaly spikes detected for the selected sellers.")
        else:
            with st.expander(
                f"Anomaly details ({len(anomaly_details):,} flagged signals)",
                expanded=False,
            ):
                st.dataframe(
                    anomaly_details,
                    hide_index=True,
                    use_container_width=True,
                )

with segments_tab:
    st.subheader("Behaviour Segments")
    if filtered_seller_metrics is None:
        st.warning("Load data/trust_analytics.db to view seller behaviour segments.")
    elif filtered_seller_metrics.empty:
        st.info("No sellers match the selected filters.")
    else:
        st.caption(
            "Portfolio view of sellers grouped into Reliable, Inconsistent, "
            "Return-Prone, and High-Risk behaviour tiers."
        )
        st.plotly_chart(
            build_segment_composition_chart(filtered_seller_metrics),
            use_container_width=True,
        )
        st.dataframe(
            build_segment_summary(filtered_seller_metrics),
            hide_index=True,
            use_container_width=True,
        )

with actions_tab:
    st.subheader("Trust-Risk Actions")
    if filtered_seller_metrics is None:
        st.warning("Load data/trust_analytics.db to generate seller action recommendations.")
    elif filtered_seller_metrics.empty:
        st.info("No sellers match the selected filters.")
    else:
        action_cards = build_action_cards(filtered_seller_metrics)
        if action_cards.empty:
            st.success("No sellers currently need Escalate, Coach, or Monitor action.")
        else:
            st.caption(f"{len(action_cards):,} flagged sellers need a recommended action.")
            for _, seller in action_cards.head(20).iterrows():
                with st.container(border=True):
                    header_col, score_col = st.columns([3, 1])
                    with header_col:
                        st.markdown(f"### {seller['action_badge']} · Seller `{seller['seller_id']}`")
                        st.caption(f"{seller['severity_label']} | Risk tier: {seller['risk_tier']}")
                    with score_col:
                        st.metric("Trust Score", f"{seller['trust_score']:.1f}")

                    st.markdown(
                        f"<div style='height: 6px; border-radius: 4px; background: {seller['severity_color']};'></div>",
                        unsafe_allow_html=True,
                    )
                    st.write("Supporting evidence")
                    for evidence in format_evidence_bullets(seller["evidence"]):
                        st.markdown(f"- {evidence}")
