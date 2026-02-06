# Schema Context (Deposit Account Events)

You must only use the columns and meanings defined below. Do not invent fields.

## Table: events

| Column | Type | Description | Sensitive |
|--------|------|-------------|-----------|
| event_id | STRING | Unique event identifier | No |
| event_ts | TIMESTAMP | Event timestamp | No |
| event_date | DATE | Partition date = DATE(event_ts) | No |
| account_id | STRING | Deposit account identifier | **YES** |
| customer_id | STRING | Customer identifier | **YES** |
| product_type | STRING | CHEQUING / SAVINGS / GIC | No |
| event_type | STRING | money_movement / interest / fee / account_status / gic_lifecycle / service_action | No |
| event_name | STRING | Detailed action (deposit, withdrawal, transfer_in, transfer_out, payment, etc.) | No |
| channel | STRING | DIGITAL / BRANCH / CALL_CENTER / BATCH | No |
| event_amount | NUMERIC | Amount for money/interest/fee events; NULL otherwise | No |
| currency | STRING | Currency code (e.g., CAD) | No |
| balance_after | NUMERIC | Balance after event (optional) | No |

## Query-Building Constraints

1. **Do NOT select `account_id` or `customer_id` in final outputs.**
2. Use them only for privacy-safe counting: `COUNT(DISTINCT account_id)`
3. Always include a date grain: `strftime(event_date, '%Y-%m') as month`
4. Filter by timeframe; if missing, default to monthly trend across available data
5. Enforce safe bucket sizes: >= 5 distinct accounts/customers per bucket (demo threshold)

## Standard Definitions (use consistently)

| Term | Definition | SQL |
|------|------------|-----|
| Inflow/Deposits | Positive money movements | `event_amount > 0 AND event_type = 'money_movement'` |
| Outflow/Withdrawals | Negative money movements | `event_amount < 0 AND event_type = 'money_movement'` |
| Net Flow | Sum of all money movements | `SUM(event_amount) WHERE event_type = 'money_movement'` |
| Transaction Count | Number of money movement events | `COUNT(*) WHERE event_type = 'money_movement'` |

## Available Data Range

The data spans **January 2024 to March 2024** (historical sample data).
- For "last month" or "recent" queries, use available data range, NOT CURRENT_DATE
- For trend queries, include all available months unless user specifies otherwise
