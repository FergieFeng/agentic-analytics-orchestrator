"""
Shared state schema for the orchestrator graph.

All agents read from and write to this state.
"""

from typing import TypedDict, Optional, List, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime


class OrchestratorState(TypedDict, total=False):
    """State shared across all agents in the graph."""
    
    # User input
    user_question: str
    
    # Scope check
    is_in_scope: bool
    scope_reason: str
    
    # Routing
    intent: str
    selected_agents: List[str]
    
    # Definition Agent output
    definition_result: Dict[str, Any]
    
    # SQL Agent output
    sql_query: str
    sql_result: Dict[str, Any]
    sql_explanation: str
    
    # Data Quality Agent output
    quality_result: Dict[str, Any]
    
    # Explanation Agent output
    explanation: Dict[str, Any]
    
    # Final output
    final_response: str
    
    # Metadata
    errors: List[str]
    trace: List[Dict[str, Any]]
    start_time: str
    end_time: str
    total_tokens: int


def create_initial_state(question: str) -> OrchestratorState:
    """Create initial state from a user question."""
    return OrchestratorState(
        user_question=question,
        is_in_scope=True,
        scope_reason="",
        intent="",
        selected_agents=[],
        definition_result={},
        sql_query="",
        sql_result={},
        sql_explanation="",
        quality_result={},
        explanation={},
        final_response="",
        errors=[],
        trace=[],
        start_time=datetime.now().isoformat(),
        end_time="",
        total_tokens=0
    )


def add_trace(state: OrchestratorState, agent: str, action: str, details: Dict = None) -> OrchestratorState:
    """Add a trace entry to the state."""
    trace_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "action": action,
        "details": details or {}
    }
    
    trace = state.get("trace", [])
    trace.append(trace_entry)
    
    return {**state, "trace": trace}
