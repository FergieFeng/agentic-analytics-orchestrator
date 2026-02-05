"""
Routing logic: determines which specialist(s) to call.
"""

from typing import List, Literal
from .state import OrchestratorState


# Intent types
IntentType = Literal[
    "metric_query",      # Simple aggregation (total, count, avg)
    "comparison",        # Compare across dimensions
    "trend",             # Time-based analysis
    "drill_down",        # Detailed breakdown
    "data_exploration",  # General exploration
]


def route_to_specialists(state: OrchestratorState) -> List[str]:
    """
    Determine which specialists to invoke based on the user question.
    
    Returns a list of specialist names to call in order.
    """
    question = state.get("user_question", "").lower()
    
    # All queries go through the main pipeline
    # Future: could skip definition_agent for simple queries
    agents = [
        "definition_agent",
        "sql_agent", 
        "data_quality_agent",
        "explanation_agent"
    ]
    
    return agents


def classify_intent(question: str) -> IntentType:
    """
    Classify the user's intent from their question.
    
    Returns: intent category
    """
    question_lower = question.lower()
    
    # Trend indicators
    if any(word in question_lower for word in ["trend", "over time", "monthly", "weekly", "daily", "growth", "change"]):
        return "trend"
    
    # Comparison indicators
    if any(word in question_lower for word in ["compare", "vs", "versus", "difference", "between"]):
        return "comparison"
    
    # Drill-down indicators
    if any(word in question_lower for word in ["breakdown", "by", "per", "each", "detail"]):
        return "drill_down"
    
    # Exploration indicators
    if any(word in question_lower for word in ["show", "list", "what are", "explore"]):
        return "data_exploration"
    
    # Default: metric query
    return "metric_query"


def should_skip_definition(state: OrchestratorState) -> bool:
    """
    Determine if we can skip the Definition Agent.
    
    Returns True for very simple queries that don't need interpretation.
    """
    question = state.get("user_question", "").lower()
    
    # Very simple pattern-based queries could skip definition
    simple_patterns = [
        "count of",
        "total number of",
        "how many",
    ]
    
    # For now, always use definition agent for better accuracy
    return False


def get_next_agent(state: OrchestratorState) -> str:
    """
    Get the next agent to call based on current state.
    
    Used for sequential execution.
    """
    selected = state.get("selected_agents", [])
    trace = state.get("trace", [])
    
    # Find agents that have already run
    completed_agents = set()
    for entry in trace:
        if entry.get("action") == "completed":
            completed_agents.add(entry.get("agent"))
    
    # Return first agent that hasn't completed
    for agent in selected:
        if agent not in completed_agents:
            return agent
    
    return "end"
