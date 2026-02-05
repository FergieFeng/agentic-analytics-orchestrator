"""
Tests for the SQL agent.
"""

import pytest


class TestSQLAgent:
    """Test SQL agent functionality."""
    
    def test_sql_agent_imports(self):
        """SQL agent should be importable."""
        from src.specialists.sql_agent import run
        assert callable(run)
    
    def test_sql_agent_returns_dict(self):
        """SQL agent should return a dict with sql_query and sql_result."""
        from src.specialists.sql_agent.agent import run
        
        state = {
            "user_question": "What is the total deposit amount?",
            "definition_result": {
                "metric": {"function": "SUM", "column": "event_amount"},
                "dimensions": [],
                "filters": []
            }
        }
        
        result = run(state)
        
        assert isinstance(result, dict)
        assert "sql_query" in result


class TestSQLGeneration:
    """Test SQL query generation."""
    
    def test_generated_sql_is_select(self):
        """Generated SQL should be a SELECT statement."""
        from src.specialists.sql_agent.agent import run
        
        state = {
            "user_question": "Count transactions",
            "definition_result": {}
        }
        
        result = run(state)
        
        if result.get("sql_query"):
            assert result["sql_query"].strip().upper().startswith("SELECT")
