"""
SQL Guard: Validate SQL queries before execution.

Prevents dangerous or malformed queries.
"""

import re
from typing import Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum

from src.tools.schema_tool import get_column_names


class SQLValidationStatus(Enum):
    """Status of SQL validation."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


@dataclass
class SQLValidationResult:
    """Result of SQL validation."""
    status: SQLValidationStatus
    reason: str
    warnings: List[str]
    sanitized_sql: Optional[str] = None
    
    @property
    def is_allowed(self) -> bool:
        """Check if the query should be allowed to execute."""
        return self.status in (SQLValidationStatus.VALID, SQLValidationStatus.WARNING)


# Allowed SQL operations
ALLOWED_OPERATIONS = ["SELECT", "WITH"]

# Disallowed SQL operations (dangerous)
DISALLOWED_OPERATIONS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", 
    "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
]

# Dangerous patterns that could indicate SQL injection
DANGEROUS_PATTERNS = [
    (r";\s*(DROP|DELETE|INSERT|UPDATE|TRUNCATE)", "Multiple statements with dangerous operation"),
    (r"--\s*$", "SQL comment at end (potential injection)"),
    (r"/\*.*\*/", "Block comment (potential injection)"),
    (r"UNION\s+ALL\s+SELECT", "UNION injection pattern"),
    (r"OR\s+1\s*=\s*1", "Always-true condition (injection pattern)"),
    (r"'\s*OR\s+'", "String-based injection pattern"),
]

# Patterns that are allowed but should generate warnings
WARNING_PATTERNS = [
    (r"SELECT\s+\*", "SELECT * may return more data than needed"),
    (r"(?<!LIMIT\s)(?<!TOP\s)\bSELECT\b(?!.*\bLIMIT\b)", "Query has no LIMIT clause"),
]


def validate_sql(sql: str, check_columns: bool = True) -> SQLValidationResult:
    """
    Validate a SQL query before execution.
    
    Args:
        sql: SQL query string
        check_columns: Whether to validate column names against schema
        
    Returns:
        SQLValidationResult with status, reason, and warnings
    """
    warnings = []
    sql_clean = sql.strip()
    sql_upper = sql_clean.upper()
    
    # Check for empty query
    if not sql_clean:
        return SQLValidationResult(
            status=SQLValidationStatus.INVALID,
            reason="Empty SQL query",
            warnings=[]
        )
    
    # Check for disallowed operations
    for op in DISALLOWED_OPERATIONS:
        if re.search(rf'\b{op}\b', sql_upper):
            return SQLValidationResult(
                status=SQLValidationStatus.INVALID,
                reason=f"Disallowed SQL operation: {op}. Only SELECT queries are permitted.",
                warnings=[]
            )
    
    # Check it starts with allowed operation
    starts_valid = any(sql_upper.startswith(op) for op in ALLOWED_OPERATIONS)
    if not starts_valid:
        return SQLValidationResult(
            status=SQLValidationStatus.INVALID,
            reason=f"Query must start with SELECT or WITH. Got: {sql_upper[:20]}...",
            warnings=[]
        )
    
    # Check for dangerous patterns
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, sql_upper):
            return SQLValidationResult(
                status=SQLValidationStatus.INVALID,
                reason=f"Potentially dangerous SQL pattern detected: {description}",
                warnings=[]
            )
    
    # Check for warning patterns
    for pattern, warning in WARNING_PATTERNS:
        if re.search(pattern, sql_upper):
            warnings.append(warning)
    
    # Validate column names if requested
    if check_columns:
        column_warnings = _check_columns(sql)
        warnings.extend(column_warnings)
    
    # Sanitize the SQL
    sanitized = sanitize_sql(sql_clean)
    
    if warnings:
        return SQLValidationResult(
            status=SQLValidationStatus.WARNING,
            reason="Query is valid but has warnings",
            warnings=warnings,
            sanitized_sql=sanitized
        )
    
    return SQLValidationResult(
        status=SQLValidationStatus.VALID,
        reason="SQL query is valid",
        warnings=[],
        sanitized_sql=sanitized
    )


def _check_columns(sql: str) -> List[str]:
    """Check if referenced columns exist in schema."""
    warnings = []
    
    try:
        valid_columns = set(get_column_names())
        
        # Extract potential column references (simple heuristic)
        # Look for words that could be column names
        words = re.findall(r'\b([a-z_][a-z0-9_]*)\b', sql.lower())
        
        # SQL keywords to ignore
        sql_keywords = {
            'select', 'from', 'where', 'and', 'or', 'not', 'in', 'is', 'null',
            'group', 'by', 'order', 'asc', 'desc', 'limit', 'offset', 'having',
            'join', 'left', 'right', 'inner', 'outer', 'on', 'as', 'distinct',
            'count', 'sum', 'avg', 'min', 'max', 'round', 'abs', 'case', 'when',
            'then', 'else', 'end', 'between', 'like', 'true', 'false', 'cast',
            'events', 'sample_events', 'data', 'csv', 'with', 'over', 'partition',
            'strftime', 'date', 'filter', 'coalesce', 'nullif'
        }
        
        for word in set(words):
            if word not in sql_keywords and word not in valid_columns:
                # Could be an invalid column reference
                if len(word) > 2:  # Ignore very short words
                    # Check if it looks like a column name pattern
                    if '_' in word or word.endswith('_id') or word.endswith('_date'):
                        warnings.append(f"Possible invalid column reference: '{word}'")
    
    except Exception:
        # If schema loading fails, skip column validation
        pass
    
    return warnings


def sanitize_sql(sql: str) -> str:
    """
    Sanitize a SQL query by removing comments and normalizing whitespace.
    
    Args:
        sql: Raw SQL query
        
    Returns:
        Sanitized SQL query
    """
    # Remove single-line comments
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    
    # Remove multi-line comments
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    
    # Normalize whitespace (but preserve string literals)
    # This is a simplified version - production would need proper SQL parsing
    sql = ' '.join(sql.split())
    
    return sql.strip()


def add_limit_if_missing(sql: str, default_limit: int = 1000) -> str:
    """
    Add a LIMIT clause if the query doesn't have one.
    
    Args:
        sql: SQL query
        default_limit: Default limit to add
        
    Returns:
        SQL with LIMIT clause
    """
    sql_upper = sql.upper()
    
    if 'LIMIT' not in sql_upper:
        sql = f"{sql.rstrip().rstrip(';')} LIMIT {default_limit}"
    
    return sql


if __name__ == "__main__":
    # Test examples
    test_queries = [
        "SELECT * FROM events LIMIT 10",
        "SELECT channel, COUNT(*) FROM events GROUP BY channel",
        "DELETE FROM events",
        "SELECT * FROM events; DROP TABLE users;",
        "SELECT * FROM events WHERE 1=1 OR '1'='1'",
        "SELECT invalid_column FROM events",
        "SELECT event_date, SUM(event_amount) FROM events GROUP BY event_date",
        "",
    ]
    
    print("=== SQL Validation Tests ===\n")
    
    for q in test_queries:
        result = validate_sql(q)
        status_icon = "✓" if result.is_allowed else "✗"
        print(f"{status_icon} Query: {q[:60]}{'...' if len(q) > 60 else ''}")
        print(f"   Status: {result.status.value}")
        print(f"   Reason: {result.reason}")
        if result.warnings:
            print(f"   Warnings: {result.warnings}")
        print()
