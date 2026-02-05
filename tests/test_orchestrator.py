"""
Tests for the orchestrator routing logic.
"""

import pytest
from src.orchestrator.router import route_to_specialists, classify_intent


class TestRouter:
    """Test routing logic."""
    
    def test_route_returns_list(self):
        """Router should return a list of agent names."""
        state = {"user_question": "What is the total deposit amount?"}
        agents = route_to_specialists(state)
        
        assert isinstance(agents, list)
        assert len(agents) > 0
    
    def test_route_includes_sql_agent(self):
        """SQL agent should be included for data queries."""
        state = {"user_question": "What is the total deposit amount?"}
        agents = route_to_specialists(state)
        
        assert "sql_agent" in agents
    
    def test_classify_intent_returns_string(self):
        """Intent classifier should return a string."""
        intent = classify_intent("What is the total deposit amount?")
        
        assert isinstance(intent, str)
        assert len(intent) > 0


class TestOrchestratorState:
    """Test orchestrator state schema."""
    
    def test_state_has_required_fields(self):
        """State should have all required fields."""
        from src.orchestrator.state import OrchestratorState
        
        # Check TypedDict has expected keys
        expected_keys = [
            "user_question",
            "intent",
            "selected_agents",
            "sql_query",
            "sql_result",
            "final_response"
        ]
        
        for key in expected_keys:
            assert key in OrchestratorState.__annotations__
