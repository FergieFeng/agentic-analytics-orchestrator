"""
Tests for the DuckDB tool.
"""

import pytest
from src.tools.duckdb_tool import execute_query, execute_query_df


class TestDuckDBTool:
    """Test DuckDB query execution."""
    
    def test_execute_query_returns_list(self):
        """Execute query should return a list of dicts."""
        result = execute_query("""
            SELECT channel, COUNT(*) as count 
            FROM 'data/sample_events.csv' 
            GROUP BY channel
        """)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], dict)
    
    def test_execute_query_has_columns(self):
        """Result should have expected columns."""
        result = execute_query("""
            SELECT channel, COUNT(*) as count 
            FROM 'data/sample_events.csv' 
            GROUP BY channel
        """)
        
        assert "channel" in result[0]
        assert "count" in result[0]
    
    def test_execute_query_invalid_sql_raises(self):
        """Invalid SQL should raise an error."""
        with pytest.raises(RuntimeError):
            execute_query("SELECT * FROM nonexistent_table")
    
    def test_execute_query_df_returns_dataframe(self):
        """Execute query DF should return a pandas DataFrame."""
        df = execute_query_df("""
            SELECT * FROM 'data/sample_events.csv' LIMIT 5
        """)
        
        assert hasattr(df, 'shape')
        assert df.shape[0] == 5


class TestQueryResults:
    """Test specific query results."""
    
    def test_channel_values(self):
        """Channels should be DIGITAL or BRANCH."""
        result = execute_query("""
            SELECT DISTINCT channel FROM 'data/sample_events.csv'
        """)
        
        channels = {r["channel"] for r in result}
        assert channels == {"DIGITAL", "BRANCH"}
    
    def test_total_rows(self):
        """Should have 40 rows in sample data."""
        result = execute_query("""
            SELECT COUNT(*) as count FROM 'data/sample_events.csv'
        """)
        
        assert result[0]["count"] == 40
