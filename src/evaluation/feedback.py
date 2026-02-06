"""
Feedback: User feedback collection and management.

Features:
- Interactive feedback prompts
- Score normalization
- Feedback storage
- Analytics helpers
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from .query_store import get_query_store


@dataclass
class FeedbackResult:
    """Result of feedback collection."""
    session_id: str
    score: int  # 1-5
    feedback: Optional[str]
    collected_at: str
    saved: bool


def normalize_score(input_value: str) -> Optional[int]:
    """
    Normalize various feedback inputs to 1-5 scale.
    
    Accepts:
    - Numbers 1-5
    - Thumbs up/down variants: "👍", "👎", "up", "down", "yes", "no"
    - Descriptive: "great", "good", "ok", "bad", "terrible"
    """
    input_lower = input_value.lower().strip()
    
    # Direct numbers
    if input_lower in ("1", "2", "3", "4", "5"):
        return int(input_lower)
    
    # Thumbs up variants (positive = 5)
    if input_lower in ("👍", "up", "yes", "y", "+", "good", "great", "excellent", "perfect"):
        return 5
    
    # Thumbs down variants (negative = 1)
    if input_lower in ("👎", "down", "no", "n", "-", "bad", "terrible", "wrong", "incorrect"):
        return 1
    
    # Middle ground
    if input_lower in ("ok", "okay", "fine", "meh", "neutral"):
        return 3
    
    # Somewhat positive
    if input_lower in ("decent", "alright", "acceptable"):
        return 4
    
    # Somewhat negative
    if input_lower in ("poor", "not great", "could be better"):
        return 2
    
    return None


def collect_feedback_interactive(session_id: str) -> Optional[FeedbackResult]:
    """
    Collect feedback interactively from the user.
    
    Args:
        session_id: The query session to rate
        
    Returns:
        FeedbackResult or None if user skips
    """
    print("\n" + "─" * 40)
    print("📝 How was this response?")
    print("   Rate 1-5, or 👍/👎, or type 'skip'")
    print("─" * 40)
    
    try:
        rating_input = input("Rating: ").strip()
        
        if not rating_input or rating_input.lower() in ("skip", "s", ""):
            print("   Skipped feedback")
            return None
        
        score = normalize_score(rating_input)
        
        if score is None:
            print(f"   Could not parse '{rating_input}', skipping")
            return None
        
        # Optional detailed feedback
        feedback_text = None
        if score <= 2:
            print("   What could be improved? (optional, press Enter to skip)")
            feedback_text = input("   Feedback: ").strip() or None
        elif score >= 4:
            print("   Any additional comments? (optional, press Enter to skip)")
            feedback_text = input("   Comment: ").strip() or None
        
        # Save to database
        store = get_query_store()
        saved = store.update_feedback(session_id, score, feedback_text)
        
        result = FeedbackResult(
            session_id=session_id,
            score=score,
            feedback=feedback_text,
            collected_at=datetime.now().isoformat(),
            saved=saved
        )
        
        if saved:
            print(f"   ✓ Saved rating: {'★' * score}{'☆' * (5 - score)}")
        else:
            print(f"   ⚠ Could not save (session not found)")
        
        return result
        
    except (KeyboardInterrupt, EOFError):
        print("\n   Cancelled")
        return None


def collect_feedback_simple(
    session_id: str, 
    score: int, 
    feedback: Optional[str] = None
) -> FeedbackResult:
    """
    Collect feedback programmatically.
    
    Args:
        session_id: The query session to rate
        score: Rating 1-5
        feedback: Optional text feedback
        
    Returns:
        FeedbackResult
    """
    if not 1 <= score <= 5:
        raise ValueError("Score must be between 1 and 5")
    
    store = get_query_store()
    saved = store.update_feedback(session_id, score, feedback)
    
    return FeedbackResult(
        session_id=session_id,
        score=score,
        feedback=feedback,
        collected_at=datetime.now().isoformat(),
        saved=saved
    )


def get_feedback_stats() -> dict:
    """Get aggregate feedback statistics."""
    store = get_query_store()
    stats = store.get_stats()
    
    # Calculate additional metrics
    total = stats.get("total_queries", 0)
    rated = int(total * stats.get("rated_percentage", 0) / 100)
    
    return {
        "total_queries": total,
        "rated_queries": rated,
        "unrated_queries": total - rated,
        "avg_user_score": stats.get("avg_user_score"),
        "avg_self_score": stats.get("avg_self_score"),
        "score_correlation": _calculate_correlation(),
        "feedback_rate": stats.get("rated_percentage")
    }


def _calculate_correlation() -> Optional[float]:
    """
    Calculate correlation between self-scores and user scores.
    
    This helps understand if the self-evaluation is accurate.
    """
    store = get_query_store()
    
    # Get records with both scores
    records = store.get_by_score_range(score_type="user")
    
    pairs = []
    for r in records:
        if r.self_score is not None and r.user_score is not None:
            pairs.append((r.self_score, r.user_score))
    
    if len(pairs) < 3:
        return None  # Not enough data
    
    # Simple Pearson correlation
    n = len(pairs)
    sum_x = sum(p[0] for p in pairs)
    sum_y = sum(p[1] for p in pairs)
    sum_xy = sum(p[0] * p[1] for p in pairs)
    sum_x2 = sum(p[0] ** 2 for p in pairs)
    sum_y2 = sum(p[1] ** 2 for p in pairs)
    
    numerator = n * sum_xy - sum_x * sum_y
    denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
    
    if denominator == 0:
        return None
    
    return round(numerator / denominator, 3)


def format_feedback_summary() -> str:
    """Format a summary of feedback statistics for display."""
    stats = get_feedback_stats()
    
    lines = [
        "📊 Feedback Summary",
        "─" * 30,
        f"Total queries:     {stats['total_queries']}",
        f"Rated queries:     {stats['rated_queries']} ({stats['feedback_rate']:.1f}%)",
    ]
    
    if stats['avg_user_score']:
        lines.append(f"Avg user rating:   {stats['avg_user_score']:.1f}/5")
    
    if stats['avg_self_score']:
        lines.append(f"Avg self score:    {stats['avg_self_score']:.1f}/100")
    
    if stats['score_correlation']:
        corr = stats['score_correlation']
        interpretation = "strong" if abs(corr) > 0.7 else "moderate" if abs(corr) > 0.4 else "weak"
        lines.append(f"Score correlation: {corr:.2f} ({interpretation})")
    
    return "\n".join(lines)


def get_improvement_insights() -> list:
    """
    Analyze feedback to identify improvement areas.
    
    Returns list of insights based on low-rated queries.
    """
    store = get_query_store()
    
    # Get low-rated queries
    low_rated = store.get_by_score_range(max_score=2, score_type="user")
    
    insights = []
    
    if not low_rated:
        insights.append("No low-rated queries found - system performing well!")
        return insights
    
    # Analyze patterns in low-rated queries
    sql_issues = 0
    empty_results = 0
    feedback_themes = []
    
    for record in low_rated:
        # Check for SQL issues
        if record.error_count > 0:
            sql_issues += 1
        
        # Check for empty results
        if record.result_summary_json:
            import json
            summary = json.loads(record.result_summary_json)
            if summary.get("row_count", 0) == 0:
                empty_results += 1
        
        # Collect feedback themes
        if record.user_feedback:
            feedback_themes.append(record.user_feedback)
    
    if sql_issues > 0:
        insights.append(f"• {sql_issues} low-rated queries had execution errors - improve SQL generation")
    
    if empty_results > 0:
        insights.append(f"• {empty_results} low-rated queries returned no data - improve value discovery")
    
    if feedback_themes:
        insights.append(f"• User feedback themes: {'; '.join(feedback_themes[:3])}")
    
    return insights
