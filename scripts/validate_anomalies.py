"""Manual review helper for anomaly validation (issue #21).

This script outputs details for 20 sellers (10 flagged, 10 not flagged)
to facilitate manual review and precision/recall computation.
"""

import pandas as pd


def main():
    # Load anomalies
    anomalies = pd.read_csv("data/processed/seller_anomalies.csv")
    metrics = pd.read_csv("data/processed/seller_metrics.csv")
    fact = pd.read_csv("data/processed/seller_order_fact.csv")
    fact["order_purchase_timestamp"] = pd.to_datetime(fact["order_purchase_timestamp"], errors="coerce")

    # Get 10 flagged and 10 non-flagged sellers
    flagged = anomalies[anomalies["any_anomaly"]]["seller_id"].head(10).tolist()
    non_flagged = anomalies[~anomalies["any_anomaly"]]["seller_id"].head(10).tolist()

    review_sellers = flagged + non_flagged

    print("=" * 80)
    print("ANOMALY VALIDATION - MANUAL REVIEW SHEET (Issue #21)")
    print("=" * 80)
    print(f"\nTotal sellers to review: {len(review_sellers)}")
    print(f"Flagged (anomaly=True): {len(flagged)}")
    print(f"Not flagged (anomaly=False): {len(non_flagged)}")
    print("\n" + "=" * 80)

    for i, seller_id in enumerate(review_sellers, 1):
        is_flagged = seller_id in flagged
        seller_metrics = metrics[metrics["seller_id"] == seller_id].iloc[0]
        seller_fact = fact[fact["seller_id"] == seller_id]

        print(f"\n[{i:2d}] Seller: {seller_id} | Flagged: {'YES' if is_flagged else 'NO'}")
        print("-" * 80)

        # Key metrics
        print(f"    Total Orders: {int(seller_metrics['total_orders'])}")
        print(f"    Late Delivery Rate: {seller_metrics['late_delivery_rate']:.4f}")
        print(f"    Avg Review Score: {seller_metrics['average_review_score']:.2f}")
        print(f"    Cancellation Rate: {seller_metrics['cancellation_rate_proxy']:.4f}")
        print(f"    Negative Review Rate: {seller_metrics['negative_review_rate']:.4f}")
        print(f"    Avg Delivery Delay: {seller_metrics['average_delivery_delay_days']:.2f} days")
        print(f"    Avg Response Time: {seller_metrics['average_response_time_hours']:.2f} hours")
        print(f"    Trust Score: {seller_metrics.get('trust_score', 'N/A')}")

        # Anomaly details if flagged
        if is_flagged:
            seller_anomaly = anomalies[anomalies["seller_id"] == seller_id].iloc[0]
            anomaly_cols = [c for c in seller_anomaly.index if c.endswith("_anomaly") and seller_anomaly[c]]
            if len(anomaly_cols) > 0:
                print(f"    ANOMALY FLAGS: {', '.join(anomaly_cols)}")

        # Recent orders sample
        recent_orders = seller_fact.nlargest(3, "order_purchase_timestamp")[
            ["order_id", "order_purchase_timestamp", "review_score", "is_late_delivery", "delivery_delay_days"]
        ]
        print("    Recent Orders:")
        for _, order in recent_orders.iterrows():
            print(
                f"      {order['order_id'][:12]}... | {str(order['order_purchase_timestamp'])[:10]} | Score: {order['review_score']} | Late: {order['is_late_delivery']} | Delay: {order['delivery_delay_days']:.1f}"
            )

    print("\n" + "=" * 80)
    print("MANUAL REVIEW INSTRUCTIONS:")
    print("=" * 80)
    print("1. For each seller, check if the anomaly flag is ACCURATE (true positive/negative)")
    print("   or INACCURATE (false positive/negative)")
    print("2. Record your assessment in the table below")
    print("3. Compute precision = TP / (TP + FP)")
    print("4. Compute recall = TP / (TP + FN)")
    print("5. Adjust Z-score threshold if precision/recall are poor")
    print("6. Document findings in docs/anomaly-validation.md")
    print("\nREVIEW TABLE:")
    print("| # | Seller ID | Flagged | Your Assessment (TP/FP/TN/FN) | Notes |")
    print("|---|-----------|---------|-------------------------------|-------|")
    for i, seller_id in enumerate(review_sellers, 1):
        is_flagged = "YES" if seller_id in flagged else "NO"
        print(f"| {i:2d} | {seller_id} | {is_flagged:7s} |                               |       |")


if __name__ == "__main__":
    main()
