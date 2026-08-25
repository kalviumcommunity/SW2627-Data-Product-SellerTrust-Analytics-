# Data Dictionary (v1)

| Field | Definition | Cleaning / constraint |
|---|---|---|
| `order_id` | Olist order identifier | Required join key; one seller-order fact record per seller and order. |
| `seller_id` | Olist seller identifier | Required seller grain. |
| `order_status` | Lifecycle status | Trimmed and lower-cased; `canceled` is the v1 cancellation/return proxy. |
| `delivery_delay_days` | Delivered date minus estimated delivery date | Positive means late; null when no delivery timestamp exists. |
| `is_late_delivery` | Whether `delivery_delay_days > 0` | Nullable boolean; missing delivery is not considered on-time. |
| `review_score` | Customer score, 1–5 | Parsed numeric; missing scores remain missing and are excluded from score-based rates. |
| `sentiment_bucket` | Score-derived sentiment | 1–2 negative; 3 neutral; 4–5 positive. Not text/NLP sentiment. |
| `response_time_hours` | Review answer time minus review creation time | Imperfect review-response proxy; not a customer-support SLA. |
| `cancellation_rate_proxy` | Canceled seller orders / seller orders | Locked v1 proxy, not a true return rate. |
| `negative_review_rate` | Reviews with score 1–2 / reviewed seller orders | Locked v1 dispute proxy, not a true dispute rate. |
| `eligible_for_risk_score` | Seller has at least five orders | Protects against unstable single-order ratings. |
