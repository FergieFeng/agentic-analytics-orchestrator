"""
Data Quality Agent: Validates query results and checks for anomalies.

Responsibilities:
- Check for null values and data completeness
- Detect potential outliers or anomalies
- Validate result reasonableness
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class QualityStatus(Enum):
    """Quality check status."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass
class QualityCheck:
    """Result of a single quality check."""
    name: str
    status: QualityStatus
    message: str
    details: Dict[str, Any] = None


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the Data Quality Agent.
    
    Args:
        state: Current state with sql_result
        
    Returns:
        dict with quality_result containing checks and overall status
    """
    sql_result = state.get("sql_result")
    
    if sql_result is None:
        return {
            "quality_result": {
                "status": QualityStatus.FAIL.value,
                "checks": [],
                "message": "No SQL result to validate"
            }
        }
    
    checks = []
    
    # Check 1: Result has data
    checks.append(_check_has_data(sql_result))
    
    # Check 2: Check for null values
    checks.append(_check_null_values(sql_result))
    
    # Check 3: Check row count reasonableness
    checks.append(_check_row_count(sql_result))
    
    # Check 4: Check for numeric anomalies
    checks.append(_check_numeric_values(sql_result))
    
    # Determine overall status
    statuses = [c.status for c in checks]
    
    if QualityStatus.FAIL in statuses:
        overall_status = QualityStatus.FAIL
        overall_message = "Data quality checks failed"
    elif QualityStatus.WARNING in statuses:
        overall_status = QualityStatus.WARNING
        overall_message = "Data quality checks passed with warnings"
    else:
        overall_status = QualityStatus.PASS
        overall_message = "All data quality checks passed"
    
    return {
        "quality_result": {
            "status": overall_status.value,
            "message": overall_message,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details
                }
                for c in checks
            ]
        }
    }


def _check_has_data(result: Dict) -> QualityCheck:
    """Check that result has data."""
    data = result.get("data", [])
    row_count = result.get("row_count", 0)
    
    if row_count == 0 or len(data) == 0:
        return QualityCheck(
            name="has_data",
            status=QualityStatus.WARNING,
            message="Query returned no results",
            details={"row_count": 0}
        )
    
    return QualityCheck(
        name="has_data",
        status=QualityStatus.PASS,
        message=f"Query returned {row_count} rows",
        details={"row_count": row_count}
    )


def _check_null_values(result: Dict) -> QualityCheck:
    """Check for null values in results."""
    data = result.get("data", [])
    columns = result.get("columns", [])
    
    if not data:
        return QualityCheck(
            name="null_check",
            status=QualityStatus.PASS,
            message="No data to check"
        )
    
    null_counts = {col: 0 for col in columns}
    
    for row in data:
        for col in columns:
            if row.get(col) is None:
                null_counts[col] += 1
    
    cols_with_nulls = {k: v for k, v in null_counts.items() if v > 0}
    
    if cols_with_nulls:
        return QualityCheck(
            name="null_check",
            status=QualityStatus.WARNING,
            message=f"Found null values in {len(cols_with_nulls)} column(s)",
            details={"null_counts": cols_with_nulls}
        )
    
    return QualityCheck(
        name="null_check",
        status=QualityStatus.PASS,
        message="No null values found"
    )


def _check_row_count(result: Dict) -> QualityCheck:
    """Check if row count is reasonable."""
    row_count = result.get("row_count", 0)
    
    if row_count > 10000:
        return QualityCheck(
            name="row_count",
            status=QualityStatus.WARNING,
            message=f"Large result set ({row_count} rows) may impact performance",
            details={"row_count": row_count}
        )
    
    if row_count == 1:
        return QualityCheck(
            name="row_count",
            status=QualityStatus.PASS,
            message="Single aggregate result",
            details={"row_count": row_count}
        )
    
    return QualityCheck(
        name="row_count",
        status=QualityStatus.PASS,
        message=f"Row count ({row_count}) is reasonable",
        details={"row_count": row_count}
    )


def _check_numeric_values(result: Dict) -> QualityCheck:
    """Check for anomalies in numeric values."""
    data = result.get("data", [])
    columns = result.get("columns", [])
    
    if not data:
        return QualityCheck(
            name="numeric_check",
            status=QualityStatus.PASS,
            message="No data to check"
        )
    
    issues = []
    
    for col in columns:
        values = [row.get(col) for row in data if isinstance(row.get(col), (int, float))]
        
        if not values:
            continue
        
        # Check for negative values in typically positive columns
        if any(k in col.lower() for k in ["count", "total", "sum"]):
            negatives = [v for v in values if v < 0]
            if negatives:
                issues.append(f"Column '{col}' has {len(negatives)} negative value(s)")
        
        # Check for extreme outliers (simple check: value > 100x median)
        if len(values) > 2:
            sorted_vals = sorted(values)
            median = sorted_vals[len(sorted_vals) // 2]
            if median > 0:
                outliers = [v for v in values if v > median * 100]
                if outliers:
                    issues.append(f"Column '{col}' may have outliers")
    
    if issues:
        return QualityCheck(
            name="numeric_check",
            status=QualityStatus.WARNING,
            message="; ".join(issues),
            details={"issues": issues}
        )
    
    return QualityCheck(
        name="numeric_check",
        status=QualityStatus.PASS,
        message="Numeric values look reasonable"
    )


if __name__ == "__main__":
    # Test the agent
    test_result = {
        "data": [
            {"channel": "DIGITAL", "total": 50000.0, "count": 100},
            {"channel": "BRANCH", "total": 30000.0, "count": 50},
            {"channel": "BATCH", "total": None, "count": 10}
        ],
        "columns": ["channel", "total", "count"],
        "row_count": 3
    }
    
    result = run({"sql_result": test_result})
    quality = result["quality_result"]
    
    print(f"Overall Status: {quality['status']}")
    print(f"Message: {quality['message']}")
    print("\nChecks:")
    for check in quality["checks"]:
        icon = "✓" if check["status"] == "pass" else "⚠" if check["status"] == "warning" else "✗"
        print(f"  {icon} {check['name']}: {check['message']}")
