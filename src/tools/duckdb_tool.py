"""
DuckDB Tool: Execute SQL queries on CSV files.

No database setup required - DuckDB reads CSV directly.
"""

import duckdb
import pandas as pd
from typing import Any, List, Dict, Optional
from dataclasses import dataclass

from src.config.settings import settings


@dataclass
class QueryResult:
    """Result of a SQL query execution."""
    success: bool
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    error: Optional[str] = None
    
    def to_df(self) -> pd.DataFrame:
        """Convert result to pandas DataFrame."""
        return pd.DataFrame(self.data)
    
    def to_markdown(self) -> str:
        """Convert result to markdown table."""
        if not self.data:
            return "_No results_"
        
        df = self.to_df()
        return df.to_markdown(index=False)


def get_connection() -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection with the data table registered."""
    conn = duckdb.connect(":memory:")
    
    # Register the CSV as a table called 'events'
    data_path = settings.get_absolute_path(settings.data_path)
    conn.execute(f"""
        CREATE TABLE events AS 
        SELECT * FROM read_csv_auto('{data_path}')
    """)
    
    return conn


def execute_query(sql: str, use_table_alias: bool = True) -> QueryResult:
    """
    Execute a SQL query using DuckDB.
    
    Args:
        sql: SQL query string
        use_table_alias: If True, replace 'sample_events' with 'events' table
        
    Returns:
        QueryResult with data, columns, and metadata
        
    Example:
        result = execute_query("SELECT * FROM events LIMIT 5")
    """
    
    try:
        conn = get_connection()
        
        # Allow queries to reference 'sample_events' as well
        if use_table_alias:
            sql = sql.replace("'data/sample_events.csv'", "events")
            sql = sql.replace("sample_events", "events")
        
        result = conn.execute(sql)
        
        # Get column names
        columns = [desc[0] for desc in result.description]
        
        # Convert to list of dicts
        rows = result.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        
        return QueryResult(
            success=True,
            data=data,
            columns=columns,
            row_count=len(data),
            error=None
        )
        
    except Exception as e:
        return QueryResult(
            success=False,
            data=[],
            columns=[],
            row_count=0,
            error=str(e)
        )


def execute_query_df(sql: str) -> pd.DataFrame:
    """
    Execute a SQL query and return as pandas DataFrame.
    
    Args:
        sql: SQL query string
        
    Returns:
        pandas DataFrame with results
    """
    result = execute_query(sql)
    if not result.success:
        raise RuntimeError(f"Query failed: {result.error}")
    return result.to_df()


def get_table_info() -> Dict[str, Any]:
    """Get information about the events table."""
    conn = get_connection()
    
    # Get column info
    columns = conn.execute("DESCRIBE events").fetchall()
    
    # Get row count
    row_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    
    # Get date range
    date_range = conn.execute("""
        SELECT MIN(event_date) as min_date, MAX(event_date) as max_date 
        FROM events
    """).fetchone()
    
    conn.close()
    
    return {
        "table_name": "events",
        "columns": [{"name": c[0], "type": c[1]} for c in columns],
        "row_count": row_count,
        "date_range": {
            "min": str(date_range[0]),
            "max": str(date_range[1])
        }
    }


if __name__ == "__main__":
    # Test query
    print("=== Table Info ===")
    info = get_table_info()
    print(f"Rows: {info['row_count']}")
    print(f"Date range: {info['date_range']}")
    print()
    
    print("=== Sample Query ===")
    result = execute_query("""
        SELECT channel, COUNT(*) as count, ROUND(SUM(event_amount), 2) as total
        FROM events
        WHERE event_type = 'money_movement'
        GROUP BY channel
        ORDER BY count DESC
    """)
    
    if result.success:
        print(result.to_markdown())
    else:
        print(f"Error: {result.error}")
