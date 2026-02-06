"""
Data Quality Agent: Validates query results and checks for anomalies.

Responsibilities:
- Check for null values and data completeness
- Detect potential outliers or anomalies
- Validate result reasonableness
- Enforce privacy thresholds (k-anonymity)
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from src.config.prompts import PRIVACY_THRESHOLD, get_privacy_rules


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
    sql_query = state.get("sql_query", "")
    
    if sql_result is None:
        return {
            "quality_result": {
                "status": QualityStatus.FAIL.value,
                "checks": [],
                "message": "No SQL result to validate",
                "privacy_compliance": {"k_anonymity_met": True, "concerns": []}
            }
        }
    
    checks = []
    privacy_concerns = []
    
    # Check 1: Result has data (pass SQL query for context)
    checks.append(_check_has_data(sql_result, sql_query))
    
    # Check 2: Check for null values
    checks.append(_check_null_values(sql_result))
    
    # Check 3: Check row count reasonableness
    checks.append(_check_row_count(sql_result))
    
    # Check 4: Check for numeric anomalies
    checks.append(_check_numeric_values(sql_result))
    
    # Check 5: Privacy compliance - k-anonymity
    privacy_check, concerns = _check_privacy_compliance(sql_result)
    checks.append(privacy_check)
    privacy_concerns.extend(concerns)
    
    # Check 6: No forbidden columns in output
    forbidden_check = _check_forbidden_columns(sql_result)
    checks.append(forbidden_check)
    if forbidden_check.status == QualityStatus.FAIL:
        privacy_concerns.append(forbidden_check.message)
    
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
    
    # Privacy compliance summary
    k_anonymity_met = privacy_check.status != QualityStatus.FAIL
    
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
            ],
            "privacy_compliance": {
                "k_anonymity_met": k_anonymity_met,
                "threshold": PRIVACY_THRESHOLD,
                "concerns": privacy_concerns
            }
        }
    }


def _check_has_data(result: Dict, sql_query: str = "") -> QualityCheck:
    """Check that result has data."""
    data = result.get("data", [])
    row_count = result.get("row_count", 0)
    
    if row_count == 0 or len(data) == 0:
        # Check if this might be due to k-anonymity filtering
        if sql_query and "HAVING COUNT(DISTINCT" in sql_query.upper():
            return QualityCheck(
                name="has_data",
                status=QualityStatus.WARNING,
                message="Query returned no results - likely due to privacy thresholds (fewer than 10 distinct accounts in each bucket)",
                details={
                    "row_count": 0,
                    "likely_cause": "k_anonymity_filter",
                    "suggestion": "Try a broader aggregation (e.g., quarterly instead of monthly, or remove dimension breakdowns)"
                }
            )
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
    privacy_rules = get_privacy_rules()
    max_rows = privacy_rules.get("max_result_rows", 200)
    
    if row_count > max_rows:
        return QualityCheck(
            name="row_count",
            status=QualityStatus.WARNING,
            message=f"Large result set ({row_count} rows) exceeds recommended limit of {max_rows}",
            details={"row_count": row_count, "max_recommended": max_rows}
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
        
        # Check for negative values in count columns
        if "count" in col.lower():
            negatives = [v for v in values if v < 0]
            if negatives:
                issues.append(f"Column '{col}' has {len(negatives)} negative value(s)")
    
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


def _check_privacy_compliance(result: Dict) -> tuple[QualityCheck, List[str]]:
    """
    Check k-anonymity compliance.
    
    For each row in aggregated results, check if the underlying
    population is >= PRIVACY_THRESHOLD distinct entities.
    """
    data = result.get("data", [])
    columns = result.get("columns", [])
    concerns = []
    
    if not data:
        return QualityCheck(
            name="privacy_k_anonymity",
            status=QualityStatus.PASS,
            message="No data to check"
        ), concerns
    
    # Look for count columns that might indicate small populations
    count_columns = [c for c in columns if "count" in c.lower() or "unique" in c.lower()]
    
    small_buckets = []
    
    for row in data:
        for col in count_columns:
            count_val = row.get(col)
            if isinstance(count_val, (int, float)) and count_val < PRIVACY_THRESHOLD:
                # Find dimension values for this row
                dim_cols = [c for c in columns if c not in count_columns]
                dim_values = {c: row.get(c) for c in dim_cols}
                small_buckets.append({
                    "column": col,
                    "count": count_val,
                    "dimensions": dim_values
                })
                concerns.append(f"Small bucket ({count_val}) found in {col} for {dim_values}")
    
    if small_buckets:
        return QualityCheck(
            name="privacy_k_anonymity",
            status=QualityStatus.WARNING,
            message=f"Found {len(small_buckets)} bucket(s) with count < {PRIVACY_THRESHOLD}",
            details={"small_buckets": small_buckets, "threshold": PRIVACY_THRESHOLD}
        ), concerns
    
    return QualityCheck(
        name="privacy_k_anonymity",
        status=QualityStatus.PASS,
        message=f"All buckets meet k-anonymity threshold (>= {PRIVACY_THRESHOLD})"
    ), concerns


def _check_forbidden_columns(result: Dict) -> QualityCheck:
    """Check that forbidden columns (identifiers) are not in output."""
    columns = result.get("columns", [])
    privacy_rules = get_privacy_rules()
    forbidden = privacy_rules.get("forbidden_output_columns", [])
    
    found_forbidden = [c for c in columns if c.lower() in [f.lower() for f in forbidden]]
    
    if found_forbidden:
        return QualityCheck(
            name="forbidden_columns",
            status=QualityStatus.FAIL,
            message=f"PRIVACY VIOLATION: Forbidden columns in output: {found_forbidden}",
            details={"forbidden_columns": found_forbidden}
        )
    
    return QualityCheck(
        name="forbidden_columns",
        status=QualityStatus.PASS,
        message="No forbidden columns in output"
    )


if __name__ == "__main__":
    # Test the agent
    test_result = {
        "data": [
            {"channel": "DIGITAL", "total": 50000.0, "unique_customers": 100},
            {"channel": "BRANCH", "total": 30000.0, "unique_customers": 50},
            {"channel": "BATCH", "total": 5000.0, "unique_customers": 5}  # Small bucket!
        ],
        "columns": ["channel", "total", "unique_customers"],
        "row_count": 3
    }
    
    result = run({"sql_result": test_result})
    quality = result["quality_result"]
    
    print(f"Overall Status: {quality['status']}")
    print(f"Message: {quality['message']}")
    print(f"\nPrivacy Compliance:")
    print(f"  k-anonymity met: {quality['privacy_compliance']['k_anonymity_met']}")
    print(f"  Concerns: {quality['privacy_compliance']['concerns']}")
    print("\nChecks:")
    for check in quality["checks"]:
        icon = "✓" if check["status"] == "pass" else "⚠" if check["status"] == "warning" else "✗"
        print(f"  {icon} {check['name']}: {check['message']}")
