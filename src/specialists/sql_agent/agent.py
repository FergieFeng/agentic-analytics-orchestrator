"""
SQL Agent: Generates and executes SQL queries.

Responsibilities:
- Convert definitions to SQL
- Execute queries via DuckDB
- Return structured results
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path

from src.config.llm import get_llm_client
from src.tools.duckdb_tool import execute_query, QueryResult
from src.tools.schema_tool import get_schema_context
from src.guardrails.sql_guard import validate_sql, add_limit_if_missing


SYSTEM_PROMPT = """You are the SQL Agent for a banking analytics system.

Your job is to generate valid SQL queries based on analytical definitions.

{schema_context}

## Data Source

The data is in a table called `events` (loaded from CSV). Use `events` as the table name.

## Your Task

Given a definition (from the Definition Agent) or a direct question, generate a SQL query.

## Output Format

Return a JSON object:
```json
{{
  "sql": "SELECT ... FROM events ...",
  "explanation": "Brief explanation of what this query does"
}}
```

## SQL Rules

1. **Table name**: Use `events` (not the CSV path)
2. **Only SELECT**: No INSERT, UPDATE, DELETE, DROP
3. **Aggregations**: Use SUM, COUNT, AVG, MIN, MAX as needed
4. **Grouping**: Always GROUP BY dimension columns
5. **Ordering**: Order results meaningfully (usually DESC for metrics)
6. **Limit**: Add LIMIT for large result sets (default 100)

## DuckDB-Specific SQL Syntax

IMPORTANT: This uses DuckDB, NOT SQLite or PostgreSQL. Use DuckDB syntax:

- **Monthly grouping**: `strftime(event_date, '%Y-%m') as month` 
- **Date extraction**: `EXTRACT(MONTH FROM event_date)`, `EXTRACT(YEAR FROM event_date)`
- **Current date**: `CURRENT_DATE` (not `DATE('now')`)
- **Date arithmetic**: `CURRENT_DATE - INTERVAL '1 month'` (not `DATE('now', '-1 month')`)
- **Date range**: `event_date >= '2024-01-01' AND event_date <= '2024-03-31'`

## Common Patterns

- Deposits: `WHERE event_amount > 0 AND event_type = 'money_movement'`
- Withdrawals: `WHERE event_amount < 0 AND event_type = 'money_movement'`  
- Net flow: `SUM(event_amount) WHERE event_type = 'money_movement'`
- Monthly grouping: `strftime(event_date, '%Y-%m') as month ... GROUP BY 1`
- Channel breakdown: `GROUP BY channel`

## CRITICAL: Data Date Range

The data spans **January 2024 to March 2024** (historical data, NOT current date).

- For "last month" or "recent" queries, DO NOT use CURRENT_DATE - use the available data range
- For trend queries, include all available months: `WHERE event_date >= '2024-01-01'`
- To show "monthly" data, DO NOT filter by specific month unless user specifies one
- Default behavior for trends: show ALL available months in the data

## Example

Definition:
```json
{{"metric": {{"function": "SUM", "column": "event_amount"}}, "dimensions": ["channel"], "filters": [{{"column": "event_amount", "operator": ">", "value": 0}}]}}
```

Response:
```json
{{
  "sql": "SELECT channel, SUM(event_amount) as total_deposits FROM events WHERE event_amount > 0 AND event_type = 'money_movement' GROUP BY channel ORDER BY total_deposits DESC",
  "explanation": "Aggregates deposit amounts by channel, ordered by highest deposits first"
}}
```"""


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the SQL Agent.
    
    Args:
        state: Current state with definition_result and/or user_question
        
    Returns:
        dict with sql_query, sql_result, and sql_explanation
    """
    definition = state.get("definition_result", {})
    question = state.get("user_question", "")
    
    # Build context
    schema_context = get_schema_context()
    
    system_prompt = SYSTEM_PROMPT.format(schema_context=schema_context)
    
    # Build user prompt
    if definition and not definition.get("error"):
        user_prompt = f"""Generate SQL for this analytical definition:

Definition:
```json
{json.dumps(definition, indent=2)}
```

Original question: "{question}"

Return your SQL query as JSON."""
    else:
        user_prompt = f"""Generate SQL to answer this question:

Question: "{question}"

Return your SQL query as JSON."""
    
    # Call LLM
    try:
        client = get_llm_client()
        response = client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True
        )
        
        # Parse response
        result = response.to_json()
        
        if result is None or "sql" not in result:
            return {
                "sql_query": None,
                "sql_result": None,
                "sql_explanation": None,
                "errors": state.get("errors", []) + ["Failed to parse SQL from LLM response"]
            }
        
        sql = result["sql"]
        explanation = result.get("explanation", "")
        
        # Validate SQL
        validation = validate_sql(sql, check_columns=True)
        
        if not validation.is_allowed:
            return {
                "sql_query": sql,
                "sql_result": None,
                "sql_explanation": explanation,
                "errors": state.get("errors", []) + [f"SQL validation failed: {validation.reason}"]
            }
        
        # Add limit if missing
        sql = add_limit_if_missing(validation.sanitized_sql or sql, default_limit=100)
        
        # Execute query
        query_result = execute_query(sql)
        
        if not query_result.success:
            return {
                "sql_query": sql,
                "sql_result": None,
                "sql_explanation": explanation,
                "errors": state.get("errors", []) + [f"Query execution failed: {query_result.error}"]
            }
        
        return {
            "sql_query": sql,
            "sql_result": {
                "data": query_result.data,
                "columns": query_result.columns,
                "row_count": query_result.row_count
            },
            "sql_explanation": explanation,
            "_sql_tokens": response.usage
        }
        
    except Exception as e:
        return {
            "sql_query": None,
            "sql_result": None,
            "sql_explanation": None,
            "errors": state.get("errors", []) + [str(e)]
        }


if __name__ == "__main__":
    # Test the agent
    test_state = {
        "user_question": "What's the total deposit amount by channel?",
        "definition_result": {
            "metric": {"function": "SUM", "column": "event_amount", "alias": "total_deposits"},
            "dimensions": ["channel"],
            "filters": [
                {"column": "event_amount", "operator": ">", "value": 0},
                {"column": "event_type", "operator": "=", "value": "money_movement"}
            ],
            "interpretation": "Total deposit amounts grouped by transaction channel"
        }
    }
    
    print("Testing SQL Agent...")
    print(f"Question: {test_state['user_question']}")
    print()
    
    result = run(test_state)
    
    print(f"SQL: {result.get('sql_query')}")
    print(f"Explanation: {result.get('sql_explanation')}")
    print(f"Result: {result.get('sql_result')}")
    if result.get("errors"):
        print(f"Errors: {result['errors']}")
