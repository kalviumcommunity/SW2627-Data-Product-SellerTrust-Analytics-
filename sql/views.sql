-- SQL Views for Seller Trust Analytics
-- These views provide pre-aggregated analytics queries for dashboards and reporting

-- =============================================================================
-- vw_seller_trust_metrics: Seller-level aggregated metrics with trust score
-- =============================================================================
-- Combines seller_metrics with computed trust_score for dashboard-ready seller profiles
-- Includes risk classification and percentile rankings for quick filtering
CREATE VIEW vw_seller_trust_metrics AS
WITH trust_scored AS (
    SELECT
        sm.seller_id,
        sm.total_orders,
        sm.cancelled_orders,
        sm.late_delivery_rate,
        sm.average_delivery_delay_days,
        sm.average_review_score,
        sm.negative_review_rate,
        sm.average_response_time_hours,
        sm.cancellation_rate_proxy,
        sm.eligible_for_risk_score,
        -- Trust score calculation (weights: delivery 30%, review 30%, cancellation 20%, negative_review 20%)
        CASE
            WHEN sm.eligible_for_risk_score = 1 THEN
                ROUND(
                    0.30 * (1 - COALESCE(sm.late_delivery_rate, 0)) * 100
                    + 0.30 * ((COALESCE(sm.average_review_score, 1) - 1) / 4) * 100
                    + 0.20 * (1 - COALESCE(sm.cancellation_rate_proxy, 0)) * 100
                    + 0.20 * (1 - COALESCE(sm.negative_review_rate, 0)) * 100
                , 2)
            ELSE NULL
        END AS trust_score
    FROM seller_metrics sm
),
ranked AS (
    SELECT
        *,
        -- Percentile rankings for quick filtering (only for eligible sellers)
        -- SQLite-compatible percentile: count of sellers with lower score / total eligible * 100
        CASE
            WHEN eligible_for_risk_score = 1 AND trust_score IS NOT NULL THEN
                ROUND(
                    (SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM trust_scored WHERE eligible_for_risk_score = 1 AND trust_score IS NOT NULL)
                     FROM trust_scored ts2
                     WHERE ts2.eligible_for_risk_score = 1
                       AND ts2.trust_score IS NOT NULL
                       AND ts2.trust_score < trust_scored.trust_score)
                )
            ELSE NULL
        END AS trust_score_percentile,
        -- Risk tier classification
        CASE
            WHEN eligible_for_risk_score = 0 THEN 'insufficient_data'
            WHEN trust_score IS NULL THEN 'insufficient_data'
            WHEN trust_score >= 80 THEN 'low_risk'
            WHEN trust_score >= 60 THEN 'medium_risk'
            WHEN trust_score >= 40 THEN 'high_risk'
            ELSE 'critical_risk'
        END AS risk_tier
    FROM trust_scored
)
SELECT
    seller_id,
    total_orders,
    cancelled_orders,
    ROUND(late_delivery_rate, 4) AS late_delivery_rate,
    ROUND(average_delivery_delay_days, 2) AS average_delivery_delay_days,
    ROUND(average_review_score, 2) AS average_review_score,
    ROUND(negative_review_rate, 4) AS negative_review_rate,
    ROUND(average_response_time_hours, 2) AS average_response_time_hours,
    ROUND(cancellation_rate_proxy, 4) AS cancellation_rate_proxy,
    eligible_for_risk_score,
    trust_score,
    trust_score_percentile,
    risk_tier
FROM ranked;


-- =============================================================================
-- vw_category_risk: Risk breakdown by product category
-- =============================================================================
-- Aggregates seller-order fact data by product category to identify
-- high-risk categories based on delivery, review, and cancellation signals
CREATE VIEW vw_category_risk AS
WITH category_agg AS (
    SELECT
        COALESCE(NULLIF(TRIM(product_category_name), ''), 'unknown') AS product_category,
        COUNT(DISTINCT seller_id) AS unique_sellers,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(item_count) AS total_items,
        SUM(item_value) AS total_gmv,
        SUM(freight_value) AS total_freight,
        -- Delivery performance
        AVG(CASE WHEN is_late_delivery = 1 THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
        AVG(delivery_delay_days) AS avg_delivery_delay_days,
        -- Review quality
        AVG(review_score) AS avg_review_score,
        AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0.0 END) AS negative_review_rate,
        AVG(response_time_hours) AS avg_response_time_hours,
        -- Cancellation
        AVG(CASE WHEN order_status = 'canceled' THEN 1.0 ELSE 0.0 END) AS cancellation_rate,
        -- Sentiment distribution
        SUM(CASE WHEN sentiment_bucket = 'positive' THEN 1 ELSE 0 END) AS positive_reviews,
        SUM(CASE WHEN sentiment_bucket = 'neutral' THEN 1 ELSE 0 END) AS neutral_reviews,
        SUM(CASE WHEN sentiment_bucket = 'negative' THEN 1 ELSE 0 END) AS negative_reviews
    FROM seller_order_fact
    GROUP BY COALESCE(NULLIF(TRIM(product_category_name), ''), 'unknown')
),
category_risk AS (
    SELECT
        *,
        -- Composite risk score per category (0-100, higher = riskier)
        ROUND(
            0.30 * COALESCE(late_delivery_rate, 0) * 100
            + 0.30 * (1 - COALESCE((avg_review_score - 1) / 4, 0)) * 100
            + 0.20 * COALESCE(cancellation_rate, 0) * 100
            + 0.20 * COALESCE(negative_review_rate, 0) * 100
        , 2) AS category_risk_score,
        -- Risk tier
        CASE
            WHEN total_orders < 10 THEN 'insufficient_data'
            WHEN (
                0.30 * COALESCE(late_delivery_rate, 0) * 100
                + 0.30 * (1 - COALESCE((avg_review_score - 1) / 4, 0)) * 100
                + 0.20 * COALESCE(cancellation_rate, 0) * 100
                + 0.20 * COALESCE(negative_review_rate, 0) * 100
            ) >= 60 THEN 'high_risk'
            WHEN (
                0.30 * COALESCE(late_delivery_rate, 0) * 100
                + 0.30 * (1 - COALESCE((avg_review_score - 1) / 4, 0)) * 100
                + 0.20 * COALESCE(cancellation_rate, 0) * 100
                + 0.20 * COALESCE(negative_review_rate, 0) * 100
            ) >= 35 THEN 'medium_risk'
            ELSE 'low_risk'
        END AS risk_tier
    FROM category_agg
)
SELECT
    product_category,
    unique_sellers,
    total_orders,
    total_items,
    ROUND(total_gmv, 2) AS total_gmv,
    ROUND(total_freight, 2) AS total_freight,
    ROUND(late_delivery_rate, 4) AS late_delivery_rate,
    ROUND(avg_delivery_delay_days, 2) AS avg_delivery_delay_days,
    ROUND(avg_review_score, 2) AS avg_review_score,
    ROUND(negative_review_rate, 4) AS negative_review_rate,
    ROUND(avg_response_time_hours, 2) AS avg_response_time_hours,
    ROUND(cancellation_rate, 4) AS cancellation_rate,
    positive_reviews,
    neutral_reviews,
    negative_reviews,
    category_risk_score,
    risk_tier
FROM category_risk
ORDER BY category_risk_score DESC;


-- =============================================================================
-- vw_monthly_trends: Time-series aggregation of key metrics
-- =============================================================================
-- Monthly rollups of seller performance metrics for trend analysis
-- Uses purchase_month from seller_order_fact for consistent time buckets
CREATE VIEW vw_monthly_trends AS
WITH monthly_fact AS (
    SELECT
        purchase_month,
        COUNT(DISTINCT order_id) AS total_orders,
        COUNT(DISTINCT seller_id) AS active_sellers,
        SUM(item_count) AS total_items,
        SUM(item_value) AS total_gmv,
        SUM(freight_value) AS total_freight,
        -- Delivery metrics
        AVG(CASE WHEN is_late_delivery = 1 THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
        AVG(delivery_delay_days) AS avg_delivery_delay_days,
        -- Review metrics
        AVG(review_score) AS avg_review_score,
        AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0.0 END) AS negative_review_rate,
        AVG(response_time_hours) AS avg_response_time_hours,
        -- Cancellation
        AVG(CASE WHEN order_status = 'canceled' THEN 1.0 ELSE 0.0 END) AS cancellation_rate,
        -- Sentiment
        SUM(CASE WHEN sentiment_bucket = 'positive' THEN 1 ELSE 0 END) AS positive_reviews,
        SUM(CASE WHEN sentiment_bucket = 'neutral' THEN 1 ELSE 0 END) AS neutral_reviews,
        SUM(CASE WHEN sentiment_bucket = 'negative' THEN 1 ELSE 0 END) AS negative_reviews
    FROM seller_order_fact
    WHERE purchase_month IS NOT NULL
    GROUP BY purchase_month
),
monthly_seller_metrics AS (
    -- Aggregate seller_metrics per month (using first order month as proxy)
    -- Note: seller_metrics doesn't have a time dimension, so we join via fact table
    SELECT
        f.purchase_month,
        COUNT(DISTINCT m.seller_id) AS sellers_with_metrics,
        AVG(m.total_orders) AS avg_orders_per_seller,
        AVG(m.late_delivery_rate) AS avg_late_delivery_rate,
        AVG(m.average_review_score) AS avg_review_score_sellers,
        AVG(m.negative_review_rate) AS avg_negative_review_rate,
        AVG(m.cancellation_rate_proxy) AS avg_cancellation_rate,
        AVG(m.average_response_time_hours) AS avg_response_time_hours_sellers
    FROM seller_order_fact f
    JOIN seller_metrics m ON f.seller_id = m.seller_id
    WHERE f.purchase_month IS NOT NULL
    GROUP BY f.purchase_month
)
SELECT
    mf.purchase_month,
    mf.total_orders,
    mf.active_sellers,
    mf.total_items,
    ROUND(mf.total_gmv, 2) AS total_gmv,
    ROUND(mf.total_freight, 2) AS total_freight,
    ROUND(mf.late_delivery_rate, 4) AS late_delivery_rate,
    ROUND(mf.avg_delivery_delay_days, 2) AS avg_delivery_delay_days,
    ROUND(mf.avg_review_score, 2) AS avg_review_score,
    ROUND(mf.negative_review_rate, 4) AS negative_review_rate,
    ROUND(mf.avg_response_time_hours, 2) AS avg_response_time_hours,
    ROUND(mf.cancellation_rate, 4) AS cancellation_rate,
    mf.positive_reviews,
    mf.neutral_reviews,
    mf.negative_reviews,
    -- Seller-level aggregates (from seller_metrics joined by month)
    COALESCE(msm.sellers_with_metrics, 0) AS sellers_with_metrics,
    ROUND(COALESCE(msm.avg_orders_per_seller, 0), 2) AS avg_orders_per_seller,
    ROUND(COALESCE(msm.avg_late_delivery_rate, 0), 4) AS avg_late_delivery_rate_sellers,
    ROUND(COALESCE(msm.avg_review_score_sellers, 0), 2) AS avg_review_score_sellers,
    ROUND(COALESCE(msm.avg_negative_review_rate, 0), 4) AS avg_negative_review_rate_sellers,
    ROUND(COALESCE(msm.avg_cancellation_rate, 0), 4) AS avg_cancellation_rate_sellers,
    ROUND(COALESCE(msm.avg_response_time_hours_sellers, 0), 2) AS avg_response_time_hours_sellers
FROM monthly_fact mf
LEFT JOIN monthly_seller_metrics msm ON mf.purchase_month = msm.purchase_month
ORDER BY mf.purchase_month;