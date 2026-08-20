# Data Validation Rules

| Dataset | Rule | Severity | Pipeline action |
|---|---|---|---|
| Orders | `order_id` is present and unique | Error | Stop the pipeline. |
| Orders | Purchase timestamp is parseable | Error | Quarantine the record for review. |
| Orders | Delivery date is not earlier than purchase date | Error | Stop the pipeline and report failed rows. |
| Orders | Delivery date is not earlier than carrier handoff | Error | Stop the pipeline and report failed rows. |
| Reviews | `review_score` is an integer from 1 through 5 when present | Error | Quarantine the record for review. |
| Reviews | Review creation date is parseable when present | Warning | Retain the record but exclude it from response-time analysis. |

The Day 8 implementation covers the four timestamp relationship rules. Dataset-level key, score-range, and quarantine checks will be added as the corresponding source tables enter the pipeline.
