"""
Tests for guardrails (scope, SQL, output).
"""

import pytest
from src.guardrails.scope_guard import check_scope
from src.guardrails.sql_guard import validate_sql, sanitize_sql
from src.guardrails.output_guard import check_output


class TestScopeGuard:
    """Test scope checking."""
    
    def test_analytics_question_in_scope(self):
        """Analytics questions should be in scope."""
        is_valid, reason = check_scope("What is the total deposit amount?")
        assert is_valid is True
    
    def test_transaction_question_in_scope(self):
        """Transaction questions should be in scope."""
        is_valid, reason = check_scope("How many transactions by channel?")
        assert is_valid is True
    
    def test_weather_question_out_of_scope(self):
        """Weather questions should be out of scope."""
        is_valid, reason = check_scope("What's the weather today?")
        assert is_valid is False
    
    def test_random_question_out_of_scope(self):
        """Random unrelated questions should be out of scope."""
        is_valid, reason = check_scope("Tell me a joke about cats")
        assert is_valid is False


class TestSQLGuard:
    """Test SQL validation."""
    
    def test_select_query_valid(self):
        """SELECT queries should be valid."""
        is_valid, reason = validate_sql(
            "SELECT * FROM 'data/sample_events.csv' LIMIT 10"
        )
        assert is_valid is True
    
    def test_delete_query_invalid(self):
        """DELETE queries should be invalid."""
        is_valid, reason = validate_sql(
            "DELETE FROM 'data/sample_events.csv'"
        )
        assert is_valid is False
    
    def test_drop_query_invalid(self):
        """DROP queries should be invalid."""
        is_valid, reason = validate_sql(
            "DROP TABLE 'data/sample_events.csv'"
        )
        assert is_valid is False
    
    def test_wrong_table_invalid(self):
        """Queries to unauthorized tables should be invalid."""
        is_valid, reason = validate_sql(
            "SELECT * FROM 'other_data.csv'"
        )
        assert is_valid is False
    
    def test_sanitize_removes_comments(self):
        """Sanitize should remove SQL comments."""
        sql = "SELECT * FROM table -- this is a comment"
        sanitized = sanitize_sql(sql)
        assert "--" not in sanitized


class TestOutputGuard:
    """Test output safety checking."""
    
    def test_normal_output_safe(self):
        """Normal analytics output should be safe."""
        is_safe, reason = check_output("Total deposits: $15,400")
        assert is_safe is True
    
    def test_dict_output_safe(self):
        """Dict output should be safe."""
        is_safe, reason = check_output({"total": 15400, "count": 10})
        assert is_safe is True
    
    def test_email_output_flagged(self):
        """Output with email should be flagged."""
        is_safe, reason = check_output("Contact: user@example.com")
        assert is_safe is False
    
    def test_ssn_pattern_flagged(self):
        """Output with SSN pattern should be flagged."""
        is_safe, reason = check_output("SSN: 123-45-6789")
        assert is_safe is False
