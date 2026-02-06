# Evaluation Package
"""
Evaluation components for query logging, scoring, and feedback.

Components:
- logger: Structured session-based logging
- query_store: SQLite database for query history
- self_eval: Automatic quality scoring
- feedback: User feedback collection
- history_search: Vector similarity search for past queries
- metrics: Performance metrics
- tracer: Call tracing
"""

from .logger import (
    SessionLogger,
    QuerySession,
    AgentTrace,
    log_event,
    log_agent_call,
    log_error
)

from .query_store import (
    QueryStore,
    QueryRecord,
    get_query_store
)

from .self_eval import (
    EvaluationResult,
    evaluate_response,
    get_confidence_explanation,
    score_to_stars
)

from .feedback import (
    FeedbackResult,
    collect_feedback_interactive,
    collect_feedback_simple,
    normalize_score,
    get_feedback_stats,
    format_feedback_summary,
    get_improvement_insights
)

from .history_search import (
    HistorySearcher,
    HistoryMatch,
    get_history_searcher,
    find_similar_queries,
    get_history_context
)

from .metrics import record_metric
from .tracer import trace_call

__all__ = [
    # Logger
    "SessionLogger",
    "QuerySession", 
    "AgentTrace",
    "log_event",
    "log_agent_call",
    "log_error",
    
    # Query Store
    "QueryStore",
    "QueryRecord",
    "get_query_store",
    
    # Self Evaluation
    "EvaluationResult",
    "evaluate_response",
    "get_confidence_explanation",
    "score_to_stars",
    
    # Feedback
    "FeedbackResult",
    "collect_feedback_interactive",
    "collect_feedback_simple",
    "normalize_score",
    "get_feedback_stats",
    "format_feedback_summary",
    "get_improvement_insights",
    
    # History Search
    "HistorySearcher",
    "HistoryMatch",
    "get_history_searcher",
    "find_similar_queries",
    "get_history_context",
    
    # Legacy
    "record_metric",
    "trace_call"
]
