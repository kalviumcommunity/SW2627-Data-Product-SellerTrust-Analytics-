import pandas as pd
import streamlit as st

from app.actions import action_queue_export, build_action_queue, format_evidence_bullets, paginate_action_queue
from app.compare import (
    build_difference_highlights,
    build_risk_badge_summary,
    build_risk_profile_chart,
    build_side_by_side_table,
    build_trust_overlay_chart,
    get_seller_options,
    prepare_compare_metrics,
)
from app.filters import RISK_TIERS, get_category_options, query_seller_metrics
from app.overview import build_overview_kpis, load_seller_metrics
from app.scorecard import add_alert_badges, build_anomaly_detail_rows
from app.segments import build_segment_composition_chart, build_segment_summary
from app.signals import (
    build_buyer_dropoff_funnel,
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
from app.ui_state import (
    get_dataset_version,
    get_last_refresh_label,
    initialise_filter_state,
    mark_data_refreshed,
    normalise_selected_option,
)
from scripts.etl_pipeline import run_etl

st.set_page_config(
    page_title="Seller Trust Analytics Dashboard",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1280px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 0.85rem;
        padding: 0.85rem 1rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
    }

    div[data-testid="stDataFrame"],
    div[data-testid="stPlotlyChart"] {
        border-radius: 0.85rem;
        overflow: hidden;
    }

    section[data-testid="stSidebar"] {
        border-right: 1px solid #e5e7eb;
    }

    @media (max-width: 900px) {
        .block-container {
            padding-left: 0.85rem;
            padding-right: 0.85rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Seller Trust Analytics Dashboard")
initialise_filter_state(st.session_state)

with st.sidebar:
    st.header("Seller Trust Analytics")
    st.write(
        "Explore seller trust signals using delivery performance, review scores, "
        "cancellation proxies, and risk indicators from the Olist e-commerce data."
    )
    st.caption("Use the dashboard tabs to move from marketplace overview to seller-level risk alerts.")
    st.divider()
    if st.button("Refresh Data", use_container_width=True):
        with st.spinner("Refreshing dashboard data..."):
            try:
                run_etl(
                    raw_dir="data/raw",
                    output_dir="data/processed",
                    db_path="data/trust_analytics.db",
                )
            except Exception as error:
                st.error(f"Refresh failed: {error}")
            else:
                mark_data_refreshed(st.session_state)
                st.cache_data.clear()
                st.success("Dashboard data refreshed successfully.")
    st.caption(get_last_refresh_label(st.session_state))
    st.caption(get_dataset_version())
    st.divider()
    seller_search = st.text_input(
        "Seller search",
        placeholder="Search seller_id",
        key="seller_search",
    )
    selected_risk_tier = st.selectbox(
        "Risk tier",
        RISK_TIERS,
        index=RISK_TIERS.index(
            normalise_selected_option(
                st.session_state,
                "selected_risk_tier",
                RISK_TIERS,
            )
        ),
        key="selected_risk_tier",
    )
    with st.spinner("Loading category filters..."):
        try:
            category_options = get_category_options()
        except FileNotFoundError:
            category_options = ["All"]
            st.warning("Load data/trust_analytics.db to enable category filtering.")
    selected_category = st.selectbox(
        "Category",
        category_options,
        index=category_options.index(
            normalise_selected_option(
                st.session_state,
                "selected_category",
                category_options,
            )
        ),
        key="selected_category",
    )

with st.spinner("Loading seller metrics..."):
    try:
        filtered_seller_metrics = query_seller_metrics(
            seller_search=seller_search,
            risk_tier=selected_risk_tier,
            category=selected_category,
        )
    except FileNotFoundError:
        filtered_seller_metrics = None
        st.warning(
            "Dashboard data is not available yet. Run the pipeline to create "
            "data/trust_analytics.db and data/processed/seller_metrics.csv."
        )
    except (KeyError, TypeError, ValueError) as error:
        filtered_seller_metrics = None
        st.error(f"Unable to query seller metrics from SQLite: {error}")

overview_tab, signals_tab, scorecard_tab, segments_tab, actions_tab, compare_tab = st.tabs(
    [
        "Trust Overview",
        "Trust vs. Behaviour Signals",
        "Seller Scorecard",
        "Behaviour Segments",
        "Trust-Risk Actions",
        "Compare Sellers",
    ]
)

with overview_tab:
    st.subheader("Trust Overview")
    with st.spinner("Loading overview metrics..."):
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
                "Return Rate uses the PRD's cancellation-rate proxy. Negative Sentiment "
                "uses the share of 1-2 star reviews."
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
            st.error("No eligible sellers match the current filters.")
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

            with st.spinner("Loading seller performance history..."):
                try:
                    order_fact = load_seller_order_fact(signal_metrics["seller_id"])
                except FileNotFoundError:
                    order_fact = None
                    st.warning("Load data/trust_analytics.db to show seller performance trends.")

            if order_fact is not None:
                st.markdown("#### Buyer Drop-Off Funnel")
                st.plotly_chart(
                    build_buyer_dropoff_funnel(order_fact),
                    use_container_width=True,
                )

                monthly_metrics = prepare_monthly_seller_metrics(order_fact)
                if monthly_metrics.empty:
                    st.warning("No monthly seller history is available for trend visuals.")
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
        st.error("No sellers match the selected filters.")
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
                    "delivered_orders_with_dates",
                    "cancellation_rate_proxy",
                    "negative_review_rate",
                    "late_delivery_rate",
                    "average_review_score",
                ]
            ],
            hide_index=True,
            use_container_width=True,
        )
        with st.spinner("Loading scorecard anomaly history..."):
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
        st.error("No sellers match the selected filters.")
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
        st.error("No sellers match the selected filters.")
    else:
        action_filter_col, sort_col, direction_col = st.columns([1, 1, 1])
        with action_filter_col:
            action_filter = st.selectbox("Action", ["All", "Escalate", "Coach", "Monitor"], key="action_filter")
        with sort_col:
            sort_by = st.selectbox(
                "Sort by", ["Severity", "Trust Score", "Total Orders", "Seller ID"], key="action_sort"
            )
        with direction_col:
            highest_first = st.checkbox("Highest priority first", value=True, key="action_direction")
        action_queue = build_action_queue(
            filtered_seller_metrics,
            action=action_filter,
            sort_by=sort_by,
            ascending=(sort_by == "Severity") == highest_first,
        )
        page_size = 20
        pages = max(1, (len(action_queue) + page_size - 1) // page_size)
        page = st.number_input("Page", min_value=1, max_value=pages, value=1, step=1)
        st.download_button(
            "Download complete action queue",
            action_queue_export(filtered_seller_metrics).to_csv(index=False).encode("utf-8"),
            "seller_action_queue.csv",
            "text/csv",
        )
        if action_queue.empty:
            st.success("No sellers currently need Escalate, Coach, or Monitor action.")
        else:
            st.caption(f"Showing page {page} of {pages} · {len(action_queue):,} flagged sellers.")
            for _, seller in paginate_action_queue(action_queue, int(page), page_size).iterrows():
                with st.container(border=True):
                    header_col, score_col = st.columns([3, 1])
                    with header_col:
                        st.markdown(f"### {seller['action_badge']} · Seller `{seller['seller_id']}`")
                        st.caption(f"{seller['severity_label']} | Risk tier: {seller['risk_tier']}")
                    with score_col:
                        score = seller["trust_score"]
                        st.metric("Trust Score", "n/a" if pd.isna(score) else f"{score:.1f}")

                    st.markdown(
                        f"<div style='height: 6px; border-radius: 4px; background: {seller['severity_color']};'></div>",
                        unsafe_allow_html=True,
                    )
                    st.write("Supporting evidence")
                    for evidence in format_evidence_bullets(seller["evidence"]):
                        st.markdown(f"- {evidence}")
                    st.caption(
                        f"Primary driver: {seller['primary_driver']} · "
                        f"Value: {seller['metric_value'] if pd.notna(seller['metric_value']) else 'n/a'} · "
                        f"Denominator: {seller['denominator'] if pd.notna(seller['denominator']) else 'n/a'}"
                    )
                    st.write(seller["explanation"])
                    st.info(f"Next step: {seller['recommended_next_step']}")

with compare_tab:
    st.subheader("Compare Sellers")
    if filtered_seller_metrics is None:
        st.warning("Load data/trust_analytics.db to compare seller metrics.")
    elif filtered_seller_metrics.empty:
        st.error("No sellers match the selected filters.")
    else:
        seller_options = get_seller_options(filtered_seller_metrics)
        default_selection = seller_options[:2]
        selected_sellers = st.multiselect(
            "Select 2-3 sellers",
            seller_options,
            default=default_selection,
            max_selections=3,
            help="Pick two or three sellers to compare metrics, trends, and risk profiles side by side.",
        )
        if len(selected_sellers) < 2:
            st.info("Select at least two sellers to enable compare mode.")
        else:
            compare_metrics = prepare_compare_metrics(filtered_seller_metrics, selected_sellers)
            st.caption("Side-by-side comparison of selected sellers using the current dashboard filters.")

            for seller in build_risk_badge_summary(compare_metrics).itertuples(index=False):
                with st.container(border=True):
                    st.markdown(f"#### Seller `{seller.seller_id}`")
                    st.markdown(
                        f"<div style='height: 6px; border-radius: 4px; background: {seller.risk_color};'></div>",
                        unsafe_allow_html=True,
                    )
                    score_col, tier_col, order_col = st.columns(3)
                    score_col.metric("Trust Score", f"{seller.trust_score:.1f}")
                    tier_col.metric("Risk Tier", seller.risk_tier)
                    order_col.metric("Orders", f"{seller.total_orders:,}")

            st.markdown("#### Side-by-Side Metrics")
            st.dataframe(
                build_side_by_side_table(compare_metrics),
                hide_index=True,
                use_container_width=True,
            )

            chart_col, diff_col = st.columns([3, 2])
            with chart_col:
                st.plotly_chart(
                    build_risk_profile_chart(compare_metrics),
                    use_container_width=True,
                )
            with diff_col:
                st.markdown("#### Key Differences")
                st.dataframe(
                    build_difference_highlights(compare_metrics),
                    hide_index=True,
                    use_container_width=True,
                )

            with st.spinner("Loading comparison history..."):
                try:
                    compare_order_fact = load_seller_order_fact(selected_sellers)
                except FileNotFoundError:
                    compare_order_fact = None
                    st.warning("Load data/trust_analytics.db to compare seller trend overlays.")

            if compare_order_fact is not None:
                compare_monthly_metrics = prepare_monthly_seller_metrics(compare_order_fact)
                if compare_monthly_metrics.empty:
                    st.warning("No monthly history is available for the selected sellers.")
                else:
                    st.markdown("#### Overlay Trend")
                    st.plotly_chart(
                        build_trust_overlay_chart(compare_monthly_metrics),
                        use_container_width=True,
                    )
