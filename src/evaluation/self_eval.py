"""
Self-Evaluation: Automatic quality scoring for query responses.

Computes confidence scores based on:
- SQL execution success
- Data quality checks
- Response completeness
- Pipeline execution status
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvaluationResult:
    """Result of self-evaluation."""
    
    # Individual scores (0-100)
    sql_valid: int = 0
    sql_executed: int = 0
    has_data: int = 0
    quality_passed: int = 0
    explanation_present: int = 0
    no_errors: int = 0
    
    # Overall score (weighted average)
    overall: float = 0.0
    
    # Confidence level
    confidence: str = "low"  # low, medium, high
    
    # Issues found
    issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql_valid": self.sql_valid,
            "sql_executed": self.sql_executed,
            "has_data": self.has_data,
            "quality_passed": self.quality_passed,
            "explanation_present": self.explanation_present,
            "no_errors": self.no_errors,
            "overall": round(self.overall, 1),
            "confidence": self.confidence,
            "issues": self.issues
        }


# Score weights
WEIGHTS = {
    "sql_valid": 0.15,
    "sql_executed": 0.20,
    "has_data": 0.20,
    "quality_passed": 0.15,
    "explanation_present": 0.15,
    "no_errors": 0.15
}


def evaluate_response(state: Dict[str, Any]) -> EvaluationResult:
    """
    Evaluate a query response and compute confidence scores.
    
    Args:
        state: Final orchestrator state
        
    Returns:
        EvaluationResult with scores and issues
    """
    result = EvaluationResult()
    
    # 1. SQL Validity
    result.sql_valid = _check_sql_valid(state)
    if result.sql_valid < 100:
        result.issues.append("SQL query had validation issues")
    
    # 2. SQL Executed Successfully
    result.sql_executed = _check_sql_executed(state)
    if result.sql_executed < 100:
        result.issues.append("SQL execution encountered errors")
    
    # 3. Has Data
    result.has_data = _check_has_data(state)
    if result.has_data < 100:
        if result.has_data == 50:
            result.issues.append("Query returned no data (may be due to privacy filtering)")
        else:
            result.issues.append("No data returned")
    
    # 4. Quality Checks Passed
    result.quality_passed = _check_quality_passed(state)
    if result.quality_passed < 100:
        result.issues.append("Some data quality checks failed")
    
    # 5. Explanation Present
    result.explanation_present = _check_explanation_present(state)
    if result.explanation_present < 100:
        result.issues.append("Missing or incomplete explanation")
    
    # 6. No Errors
    result.no_errors = _check_no_errors(state)
    if result.no_errors < 100:
        result.issues.append(f"Pipeline errors occurred")
    
    # Calculate weighted overall score
    result.overall = (
        WEIGHTS["sql_valid"] * result.sql_valid +
        WEIGHTS["sql_executed"] * result.sql_executed +
        WEIGHTS["has_data"] * result.has_data +
        WEIGHTS["quality_passed"] * result.quality_passed +
        WEIGHTS["explanation_present"] * result.explanation_present +
        WEIGHTS["no_errors"] * result.no_errors
    )
    
    # Determine confidence level
    if result.overall >= 80:
        result.confidence = "high"
    elif result.overall >= 50:
        result.confidence = "medium"
    else:
        result.confidence = "low"
    
    return result


def _check_sql_valid(state: Dict) -> int:
    """Check if SQL was generated and validated."""
    sql_query = state.get("sql_query")
    
    if not sql_query:
        return 0
    
    # Check if SQL validation passed (no blocked operations)
    sql_explanation = state.get("sql_explanation", "")
    if "error" in sql_explanation.lower() or "invalid" in sql_explanation.lower():
        return 50
    
    # Check for basic SQL structure
    sql_upper = sql_query.upper()
    if "SELECT" in sql_upper:
        return 100
    
    return 50


def _check_sql_executed(state: Dict) -> int:
    """Check if SQL executed successfully."""
    sql_result = state.get("sql_result") or {}
    
    if not sql_result:
        return 0
    
    # Check for explicit success flag
    if sql_result.get("success") is True:
        return 100
    elif sql_result.get("success") is False:
        return 0
    
    # Check for error field
    if sql_result.get("error"):
        return 0
    
    # If we have columns and data, assume success
    if sql_result.get("columns"):
        return 100
    
    return 50


def _check_has_data(state: Dict) -> int:
    """Check if query returned data."""
    sql_result = state.get("sql_result") or {}
    
    if not sql_result:
        return 0
    
    row_count = sql_result.get("row_count", 0)
    data = sql_result.get("data", [])
    
    if row_count > 0 or len(data) > 0:
        return 100
    
    # Empty results might be due to privacy filtering
    # Check if SQL has HAVING clause (k-anonymity)
    sql_query = state.get("sql_query", "").upper()
    if "HAVING" in sql_query and "COUNT" in sql_query:
        return 50  # Partial credit - valid query but no data due to privacy
    
    return 0


def _check_quality_passed(state: Dict) -> int:
    """Check data quality agent results."""
    quality_result = state.get("quality_result") or {}
    
    if not quality_result:
        return 50  # No quality check is neutral
    
    status = quality_result.get("status", "").lower()
    
    if status == "pass":
        return 100
    elif status == "warning":
        return 75
    elif status == "fail":
        return 25
    
    # Check individual checks
    checks = quality_result.get("checks", [])
    if not checks:
        return 50
    
    passed = sum(1 for c in checks if c.get("passed", False))
    total = len(checks)
    
    if total > 0:
        return int((passed / total) * 100)
    
    return 50


def _check_explanation_present(state: Dict) -> int:
    """Check if explanation was generated."""
    explanation = state.get("explanation") or {}
    final_response = state.get("final_response", "")
    
    # Check explanation object
    if explanation:
        summary = explanation.get("summary", "")
        insights = explanation.get("insights", [])
        
        if summary and len(summary) > 20:
            if insights and len(insights) > 0:
                return 100
            return 75
        return 50
    
    # Fall back to final response
    if final_response and len(final_response) > 50:
        # Check if it's just an error message
        if "error" in final_response.lower() or "could not" in final_response.lower():
            return 25
        return 75
    
    return 0


def _check_no_errors(state: Dict) -> int:
    """Check if pipeline had errors."""
    errors = state.get("errors", [])
    
    if not errors:
        return 100
    
    # Penalize based on number of errors
    if len(errors) == 1:
        return 50
    elif len(errors) == 2:
        return 25
    else:
        return 0


def get_confidence_explanation(result: EvaluationResult) -> str:
    """Generate a human-readable confidence explanation."""
    
    explanations = []
    
    if result.confidence == "high":
        explanations.append("✓ High confidence in this response")
    elif result.confidence == "medium":
        explanations.append("◐ Moderate confidence - some checks had issues")
    else:
        explanations.append("✗ Low confidence - significant issues detected")
    
    # Add specific feedback
    if result.sql_executed == 100 and result.has_data == 100:
        explanations.append("  • Query executed successfully with results")
    elif result.sql_executed == 100 and result.has_data < 100:
        explanations.append("  • Query executed but returned no data")
    elif result.sql_executed < 100:
        explanations.append("  • SQL execution had issues")
    
    if result.quality_passed < 75:
        explanations.append("  • Data quality checks raised concerns")
    
    if result.no_errors < 100:
        explanations.append(f"  • Pipeline encountered {100 - result.no_errors}% error rate")
    
    return "\n".join(explanations)


def score_to_stars(score: float) -> str:
    """Convert score to star rating display."""
    if score >= 90:
        return "★★★★★"
    elif score >= 70:
        return "★★★★☆"
    elif score >= 50:
        return "★★★☆☆"
    elif score >= 30:
        return "★★☆☆☆"
    else:
        return "★☆☆☆☆"
