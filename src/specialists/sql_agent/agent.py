"""
SQL Agent: Generates and executes SQL queries.

Uses RAG to retrieve relevant SQL patterns and metric definitions
for more accurate query generation.

Responsibilities:
- Discover actual values in data (Value Discovery step)
- Convert definitions to SQL using RAG context
- Apply privacy constraints (no identifiers, k-anonymity)
- Execute queries via DuckDB
- Return structured results
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.config.llm import get_llm_client
from src.config.prompts import AgentPrompts, get_privacy_rules
from src.tools.duckdb_tool import execute_query
from src.tools.schema_tool import load_schema
from src.guardrails.sql_guard import validate_sql, add_limit_if_missing
from src.rag import get_retriever


# Columns that benefit from value discovery
DISCOVERABLE_COLUMNS = [
    "event_type", "event_name", "channel", "product_type", "currency"
]

# Discovery constraints
DISCOVERY_LIMIT = 50
DISCOVERY_TIME_WINDOW_DAYS = 90


def discover_column_values(columns: List[str], time_window_days: int = DISCOVERY_TIME_WINDOW_DAYS) -> Dict[str, List[str]]:
    """
    Discover actual values for categorical columns.
    
    Performs limited SELECT DISTINCT queries to find real values in the data.
    Uses time windows and limits for safety.
    
    Args:
        columns: List of column names to discover values for
        time_window_days: Restrict discovery to recent N days
        
    Returns:
        Dict mapping column names to lists of discovered values
    """
    discovered = {}
    
    for col in columns:
        if col not in DISCOVERABLE_COLUMNS:
            continue
            
        try:
            # Build discovery query with time window and limit
            sql = f"""
                SELECT DISTINCT {col} as value, COUNT(*) as cnt
                FROM events
                WHERE {col} IS NOT NULL
                  AND event_date >= (SELECT MAX(event_date) - INTERVAL '{time_window_days} days' FROM events)
                GROUP BY {col}
                ORDER BY cnt DESC
                LIMIT {DISCOVERY_LIMIT}
            """
            
            result = execute_query(sql)
            
            if result.success and result.data:
                discovered[col] = [row["value"] for row in result.data]
            
        except Exception as e:
            # Discovery is optional, don't fail the whole query
            discovered[col] = []
    
    return discovered


def discover_date_range() -> Dict[str, str]:
    """
    Discover the actual date range in the data.
    
    Returns:
        Dict with min_date and max_date
    """
    try:
        sql = """
            SELECT 
                MIN(event_date) as min_date,
                MAX(event_date) as max_date,
                COUNT(DISTINCT event_date) as num_days
            FROM events
        """
        
        result = execute_query(sql)
        
        if result.success and result.data:
            row = result.data[0]
            return {
                "min_date": str(row.get("min_date", "")),
                "max_date": str(row.get("max_date", "")),
                "num_days": row.get("num_days", 0)
            }
    except Exception:
        pass
    
    return {"min_date": "", "max_date": "", "num_days": 0}


def discover_values_for_definition(definition: Dict[str, Any]) -> Dict[str, Any]:
    """
    Discover relevant values based on the query definition.
    
    Analyzes filters and dimensions to determine which columns need discovery.
    
    Args:
        definition: The definition from Definition Agent
        
    Returns:
        Dict with discovered values and metadata
    """
    discovery_result = {
        "column_values": {},
        "date_range": {},
        "discovery_notes": []
    }
    
    # 1. Discover date range
    discovery_result["date_range"] = discover_date_range()
    
    # 2. Identify columns that need value discovery
    columns_to_discover = set()
    
    # From dimensions
    dimensions = definition.get("dimensions", [])
    for dim in dimensions:
        if dim in DISCOVERABLE_COLUMNS:
            columns_to_discover.add(dim)
    
    # From filters (can be dict {"column": "condition"} or list of strings/dicts)
    filters = definition.get("filters", [])
    if isinstance(filters, dict):
        # Format: {"column_name": "condition"}
        for col in filters.keys():
            if col in DISCOVERABLE_COLUMNS:
                columns_to_discover.add(col)
    elif isinstance(filters, list):
        for f in filters:
            if isinstance(f, str):
                # Format: ["column_name", ...] or ["column_name = value", ...]
                col = f.split()[0].strip("'\"")
                if col in DISCOVERABLE_COLUMNS:
                    columns_to_discover.add(col)
            elif isinstance(f, dict):
                # Format: [{"column": "col_name", ...}, ...]
                col = f.get("column", "")
                if col in DISCOVERABLE_COLUMNS:
                    columns_to_discover.add(col)
    
    # Always discover event_type and event_name if not already specified
    if "event_type" not in columns_to_discover:
        columns_to_discover.add("event_type")
    
    # 3. Perform discovery
    if columns_to_discover:
        discovery_result["column_values"] = discover_column_values(list(columns_to_discover))
        
        for col, values in discovery_result["column_values"].items():
            if values:
                discovery_result["discovery_notes"].append(
                    f"Found {len(values)} distinct values for '{col}': {values[:5]}{'...' if len(values) > 5 else ''}"
                )
    
    return discovery_result


def format_discovery_context(discovery: Dict[str, Any]) -> str:
    """
    Format discovery results for inclusion in LLM prompt.
    
    Args:
        discovery: Results from discover_values_for_definition
        
    Returns:
        Formatted string for prompt
    """
    lines = ["## Discovered Data Context"]
    
    # Date range
    date_range = discovery.get("date_range", {})
    if date_range.get("min_date"):
        lines.append(f"\n**Available Date Range:** {date_range['min_date']} to {date_range['max_date']} ({date_range.get('num_days', 0)} days)")
    
    # Column values
    column_values = discovery.get("column_values", {})
    if column_values:
        lines.append("\n**Actual Values in Data:**")
        for col, values in column_values.items():
            if values:
                values_str = ", ".join(f"'{v}'" for v in values[:10])
                if len(values) > 10:
                    values_str += f" ... ({len(values)} total)"
                lines.append(f"- `{col}`: {values_str}")
    
    # Notes
    notes = discovery.get("discovery_notes", [])
    if notes:
        lines.append("\n**Discovery Notes:**")
        for note in notes:
            lines.append(f"- {note}")
    
    return "\n".join(lines)


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the SQL Agent with RAG-augmented context.
    
    Steps:
    1. RAG Retrieval - Get relevant SQL patterns and metrics
    2. Value Discovery - Find actual values in the data
    3. Query Generation - Generate SQL using discovered context
    4. Validation - Validate SQL against guardrails
    5. Execution - Run query via DuckDB
    
    Args:
        state: Current state with definition_result and/or user_question
        
    Returns:
        dict with sql_query, sql_result, and sql_explanation
    """
    definition = state.get("definition_result", {})
    question = state.get("user_question", "")
    
    # --- Step 0: RAG Retrieval ---
    rag_context = ""
    rag_metadata = {}
    try:
        retriever = get_retriever()
        rag_result = retriever.retrieve_for_sql(question)
        rag_context = rag_result.get_context_string(max_chunks=6)
        rag_metadata = rag_result.get_metadata_summary()
    except Exception as e:
        rag_context = ""
        rag_metadata = {"error": str(e)}
    
    # --- Step 1: Value Discovery ---
    discovery = {}
    discovery_context = ""
    
    if definition and not definition.get("error"):
        discovery = discover_values_for_definition(definition)
        discovery_context = format_discovery_context(discovery)
    else:
        # Basic discovery even without definition
        discovery = {
            "date_range": discover_date_range(),
            "column_values": discover_column_values(["event_type", "event_name", "channel"])
        }
        discovery_context = format_discovery_context(discovery)
    
    # --- Step 2: Query Generation ---
    
    # Get composed prompt (system + schema + SQL safety guardrail + agent-specific)
    system_prompt = AgentPrompts.sql()
    
    # Get privacy rules
    privacy_rules = get_privacy_rules()
    
    # Build user prompt with RAG and discovery context
    if definition and not definition.get("error"):
        user_prompt = f"""Generate a privacy-safe SQL query for this analytical definition.

{rag_context}

{discovery_context}

**Definition:**
```json
{json.dumps(definition, indent=2)}
```

**Original question:** "{question}"

**Privacy requirements:**
- k-anonymity threshold: {privacy_rules['k_anonymity_threshold']} distinct entities per bucket
- Never include {privacy_rules['forbidden_output_columns']} in output columns
- Max result rows: {privacy_rules['max_result_rows']}
- Use aggregations only

**Important:**
- Use the retrieved SQL patterns and metrics from the knowledge base
- Use the discovered values above to ensure correct filters
- If filtering on event_type, use one of the discovered event_type values
- Use the actual date range available in the data, not CURRENT_DATE

Return your SQL query as JSON with: sql, explanation, privacy_check"""
    else:
        user_prompt = f"""Generate a privacy-safe SQL query to answer this question.

{rag_context}

{discovery_context}

**Question:** "{question}"

**Privacy requirements:**
- k-anonymity threshold: {privacy_rules['k_anonymity_threshold']} distinct entities per bucket
- Never include customer_id or account_id in output columns
- Use aggregations only

**Important:**
- Use the retrieved SQL patterns and metrics from the knowledge base
- Use the discovered values above to ensure correct filters

Return your SQL query as JSON with: sql, explanation, privacy_check"""
    
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
                "value_discovery": discovery,
                "errors": state.get("errors", []) + ["Failed to parse SQL from LLM response"]
            }
        
        sql = result["sql"]
        explanation = result.get("explanation", "")
        privacy_check = result.get("privacy_check", "")
        
        # --- Step 3: Validation ---
        validation = validate_sql(sql, check_columns=True)
        
        if not validation.is_allowed:
            return {
                "sql_query": sql,
                "sql_result": None,
                "sql_explanation": explanation,
                "value_discovery": discovery,
                "errors": state.get("errors", []) + [f"SQL validation failed: {validation.reason}"]
            }
        
        # Add limit if missing
        sql = add_limit_if_missing(validation.sanitized_sql or sql, default_limit=100)
        
        # --- Step 4: Execution ---
        query_result = execute_query(sql)
        
        if not query_result.success:
            return {
                "sql_query": sql,
                "sql_result": None,
                "sql_explanation": explanation,
                "value_discovery": discovery,
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
            "privacy_check": privacy_check,
            "value_discovery": discovery,
            "_sql_tokens": response.usage,
            "_rag_metadata": rag_metadata
        }
        
    except Exception as e:
        return {
            "sql_query": None,
            "sql_result": None,
            "sql_explanation": None,
            "value_discovery": discovery,
            "errors": state.get("errors", []) + [str(e)]
        }


if __name__ == "__main__":
    # Test value discovery
    print("=== Testing Value Discovery ===\n")
    
    # Discover date range
    date_range = discover_date_range()
    print(f"Date range: {date_range}")
    
    # Discover column values
    columns = ["event_type", "event_name", "channel", "product_type"]
    values = discover_column_values(columns)
    
    print("\nDiscovered values:")
    for col, vals in values.items():
        print(f"  {col}: {vals}")
    
    # Test full agent
    print("\n=== Testing SQL Agent ===\n")
    
    test_state = {
        "user_question": "What's the breakdown of transactions by event type?",
        "definition_result": {
            "metric": {"function": "COUNT", "column": "*", "alias": "transaction_count"},
            "dimensions": ["event_type"],
            "filters": [],
            "interpretation": "Count of events grouped by event type"
        }
    }
    
    result = run(test_state)
    
    print(f"SQL: {result.get('sql_query')}")
    print(f"\nDiscovery used:")
    for col, vals in result.get("value_discovery", {}).get("column_values", {}).items():
        print(f"  {col}: {vals[:5]}")
    print(f"\nResult: {result.get('sql_result')}")
