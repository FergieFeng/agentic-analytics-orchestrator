"""
LangGraph state machine for the orchestrator.

This is the main entry point that defines the agent workflow.
"""

from typing import Dict, Any, Literal, Optional
from datetime import datetime
import time

from langgraph.graph import StateGraph, END

from .state import OrchestratorState, create_initial_state, add_trace
from .router import route_to_specialists, classify_intent
from src.guardrails.scope_guard import check_scope
from src.specialists.definition_agent import agent as definition_agent
from src.specialists.sql_agent import agent as sql_agent
from src.specialists.data_quality_agent import agent as data_quality_agent
from src.specialists.explanation_agent import agent as explanation_agent
from src.evaluation.logger import SessionLogger
from src.evaluation.self_eval import evaluate_response
from src.evaluation.query_store import get_query_store


# --- Node Functions ---

def scope_check_node(state: OrchestratorState) -> Dict[str, Any]:
    """Check if question is in scope."""
    question = state.get("user_question", "")
    
    result = check_scope(question)
    
    state = add_trace(state, "scope_guard", "checked", {
        "status": result.status.value,
        "confidence": result.confidence
    })
    
    return {
        **state,
        "is_in_scope": result.is_allowed,
        "scope_reason": result.reason
    }


def router_node(state: OrchestratorState) -> Dict[str, Any]:
    """Route to appropriate specialists."""
    question = state.get("user_question", "")
    
    intent = classify_intent(question)
    agents = route_to_specialists(state)
    
    state = add_trace(state, "router", "routed", {
        "intent": intent,
        "agents": agents
    })
    
    return {
        **state,
        "intent": intent,
        "selected_agents": agents
    }


def definition_node(state: OrchestratorState) -> Dict[str, Any]:
    """Run Definition Agent."""
    state = add_trace(state, "definition_agent", "started")
    
    result = definition_agent.run(state)
    
    # Track tokens
    tokens = result.get("definition_result", {}).get("_tokens", {})
    total_tokens = state.get("total_tokens", 0) + tokens.get("total_tokens", 0)
    
    state = add_trace(state, "definition_agent", "completed", {
        "interpretation": result.get("definition_result", {}).get("interpretation")
    })
    
    return {**state, **result, "total_tokens": total_tokens}


def sql_node(state: OrchestratorState) -> Dict[str, Any]:
    """Run SQL Agent."""
    state = add_trace(state, "sql_agent", "started")
    
    result = sql_agent.run(state)
    
    # Track tokens
    tokens = result.get("_sql_tokens", {})
    total_tokens = state.get("total_tokens", 0) + tokens.get("total_tokens", 0)
    
    sql_result = result.get("sql_result") or {}
    state = add_trace(state, "sql_agent", "completed", {
        "sql": result.get("sql_query"),
        "row_count": sql_result.get("row_count") if sql_result else None
    })
    
    # Check for errors
    errors = state.get("errors", [])
    if result.get("errors"):
        errors = errors + result["errors"]
    
    return {**state, **result, "total_tokens": total_tokens, "errors": errors}


def data_quality_node(state: OrchestratorState) -> Dict[str, Any]:
    """Run Data Quality Agent."""
    state = add_trace(state, "data_quality_agent", "started")
    
    result = data_quality_agent.run(state)
    
    state = add_trace(state, "data_quality_agent", "completed", {
        "status": result.get("quality_result", {}).get("status")
    })
    
    return {**state, **result}


def explanation_node(state: OrchestratorState) -> Dict[str, Any]:
    """Run Explanation Agent."""
    state = add_trace(state, "explanation_agent", "started")
    
    result = explanation_agent.run(state)
    
    # Track tokens
    tokens = result.get("explanation", {}).get("_tokens", {})
    total_tokens = state.get("total_tokens", 0) + tokens.get("total_tokens", 0)
    
    state = add_trace(state, "explanation_agent", "completed")
    
    return {**state, **result, "total_tokens": total_tokens}


def format_response_node(state: OrchestratorState) -> Dict[str, Any]:
    """Format the final response."""
    
    # Use the explanation agent's formatter
    final_response = explanation_agent.format_answer(state)
    
    return {
        **state,
        "final_response": final_response,
        "end_time": datetime.now().isoformat()
    }


def reject_node(state: OrchestratorState) -> Dict[str, Any]:
    """Handle out-of-scope questions."""
    from src.guardrails.scope_guard import format_rejection_message, ScopeCheckResult, ScopeStatus
    
    result = ScopeCheckResult(
        status=ScopeStatus.OUT_OF_SCOPE,
        reason=state.get("scope_reason", "Question is out of scope"),
        confidence=0.9
    )
    
    final_response = format_rejection_message(result)
    
    return {
        **state,
        "final_response": final_response,
        "end_time": datetime.now().isoformat()
    }


# --- Routing Functions ---

def route_after_scope(state: OrchestratorState) -> Literal["router", "reject"]:
    """Route based on scope check result."""
    if state.get("is_in_scope", False):
        return "router"
    return "reject"


def route_after_sql(state: OrchestratorState) -> Literal["data_quality", "format_response"]:
    """Route based on SQL execution result."""
    errors = state.get("errors", [])
    sql_result = state.get("sql_result", {})
    
    # If there are errors, skip to format response
    if errors or not sql_result:
        return "format_response"
    
    return "data_quality"


# --- Graph Definition ---

def create_graph() -> StateGraph:
    """Create and return the orchestrator graph."""
    
    # Create the graph
    graph = StateGraph(OrchestratorState)
    
    # Add nodes
    graph.add_node("scope_check", scope_check_node)
    graph.add_node("router", router_node)
    graph.add_node("definition", definition_node)
    graph.add_node("sql", sql_node)
    graph.add_node("data_quality", data_quality_node)
    graph.add_node("explanation", explanation_node)
    graph.add_node("format_response", format_response_node)
    graph.add_node("reject", reject_node)
    
    # Add edges
    graph.set_entry_point("scope_check")
    
    # Conditional edge after scope check
    graph.add_conditional_edges(
        "scope_check",
        route_after_scope,
        {
            "router": "router",
            "reject": "reject"
        }
    )
    
    # Sequential flow through agents
    graph.add_edge("router", "definition")
    graph.add_edge("definition", "sql")
    
    # Conditional edge after SQL
    graph.add_conditional_edges(
        "sql",
        route_after_sql,
        {
            "data_quality": "data_quality",
            "format_response": "format_response"
        }
    )
    
    graph.add_edge("data_quality", "explanation")
    graph.add_edge("explanation", "format_response")
    
    # End nodes
    graph.add_edge("format_response", END)
    graph.add_edge("reject", END)
    
    return graph.compile()


# Global compiled graph (lazy loaded)
_graph = None


def get_graph():
    """Get or create the compiled graph."""
    global _graph
    if _graph is None:
        _graph = create_graph()
    return _graph


def run_query(question: str, enable_logging: bool = True) -> Dict[str, Any]:
    """
    Run a query through the orchestrator.
    
    Args:
        question: User's analytics question
        enable_logging: Whether to log the session (default True)
        
    Returns:
        Final state with all results, including:
        - session_id: Unique identifier for this query
        - self_scores: Automatic quality evaluation
    """
    graph = get_graph()
    initial_state = create_initial_state(question)
    
    # Start logging session
    session_logger = None
    if enable_logging:
        session_logger = SessionLogger.start(question)
    
    # Run the graph
    start_time = time.time()
    final_state = graph.invoke(initial_state)
    elapsed_ms = (time.time() - start_time) * 1000
    
    # Self-evaluation
    eval_result = evaluate_response(final_state)
    final_state["self_scores"] = eval_result.to_dict()
    final_state["confidence"] = eval_result.confidence
    
    # Finish logging and save to database
    session_id = None
    if session_logger:
        session = SessionLogger.get_current()
        if session:
            session.self_scores = eval_result.to_dict()
            session.total_duration_ms = elapsed_ms
            session_logger.finish(final_state)
            
            # Save to query store
            try:
                store = get_query_store()
                store.save_session(session)
                session_id = session.session_id
            except Exception as e:
                # Don't fail the query due to logging issues
                pass
    
    # Add session_id to state for feedback collection
    final_state["session_id"] = session_id
    
    return final_state


if __name__ == "__main__":
    # Test the graph
    print("Testing Orchestrator Graph...")
    
    test_questions = [
        "What is the total deposit amount by channel?",
        "What's the weather today?",
    ]
    
    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"Question: {q}")
        print("="*60)
        
        result = run_query(q)
        
        print(f"\nFinal Response:\n{result.get('final_response', 'No response')}")
        print(f"\nTokens used: {result.get('total_tokens', 0)}")
