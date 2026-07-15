# Spreadsheet Data Quality Audit Summary

- State: `AUDIT_GENERATED_NOT_CLIENT_DELIVERED`
- Source file: `fictional-orders-with-issues.xlsx`
- Worksheet: `Orders`
- Scanned: 26 data rows × 6 columns
- Issue categories: 16
- High / medium / review: 10 / 4 / 2
- Original data-row cell values copied into this report: no
- Metadata retained: source file name, worksheet, headers/selected columns, row references, counts, and hashes
- External actions or connections: none

## Findings

| Severity | Code | Column | Count | Row references |
|---|---|---|---:|---|
| HIGH | CELL_ERROR | paid_amount | 1 | 19 |
| HIGH | DATE_VALUE_INVALID | order_date | 1 | 11 |
| HIGH | DUPLICATE_KEY | order_id | 2 | 4, 5 |
| HIGH | KEY_VALUE_MISSING | order_id | 1 | 21 |
| HIGH | NUMERIC_VALUE_INVALID | order_amount | 1 | 13 |
| HIGH | NUMERIC_VALUE_INVALID | paid_amount | 1 | 19 |
| HIGH | REQUIRED_VALUE_MISSING | customer_code | 2 | 7, 21 |
| HIGH | REQUIRED_VALUE_MISSING | order_amount | 1 | 21 |
| HIGH | REQUIRED_VALUE_MISSING | order_date | 1 | 21 |
| HIGH | REQUIRED_VALUE_MISSING | order_id | 1 | 21 |
| MEDIUM | EMPTY_ROW | — | 1 | 21 |
| MEDIUM | MIXED_VALUE_TYPES | order_amount | 25 | — |
| MEDIUM | MIXED_VALUE_TYPES | order_date | 25 | — |
| MEDIUM | OUTER_WHITESPACE | customer_code | 1 | 9 |
| REVIEW | NUMERIC_OUTLIER | order_amount | 1 | 16 |
| REVIEW | NUMERIC_OUTLIER | paid_amount | 2 | 23, 26 |

## Boundary

This is a rule-based preflight, not an accounting audit, compliance review, or guarantee that every business error was detected. Validate material findings against the authorized source and documented business rules.
