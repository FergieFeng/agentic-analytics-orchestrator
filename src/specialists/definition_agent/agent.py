"""
Definition Agent: Interprets metrics, dimensions, and analytical intent.

Uses RAG to retrieve relevant business glossary and metric definitions
before interpreting user questions.

Responsibilities:
- Parse user questions to identify requested metrics
- Map business terms to table columns using RAG-retrieved context
- Clarify ambiguous requests
- Flag privacy concerns early
"""

import json
from typing import Dict, Any
from pathlib import Path

from src.config.llm import get_llm_client
from src.config.prompts import AgentPrompts
from src.rag import get_retriever, RAGRetriever


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the Definition Agent with RAG-augmented context.
    
    Args:
        state: Current orchestrator state with user_question
        
    Returns:
        dict with definition_result to merge into state
    """
    question = state.get("user_question", "")
    
    if not question:
        return {
            "definition_result": {
                "error": "No question provided",
                "interpretation": None
            }
        }
    
    # --- RAG: Retrieve relevant context ---
    try:
        retriever = get_retriever()
        rag_result = retriever.retrieve_for_definition(question)
        rag_context = rag_result.get_context_string(max_chunks=8)
        rag_metadata = rag_result.get_metadata_summary()
    except Exception as e:
        # If RAG fails, continue without context
        rag_context = ""
        rag_metadata = {"error": str(e)}
    
    # Get composed prompt (system + schema + agent-specific)
    system_prompt = AgentPrompts.definition()
    
    # Build user prompt with RAG context
    user_prompt = f"""Analyze this analytics question and provide a structured definition.

## Retrieved Context (from knowledge base)
{rag_context if rag_context else "(No additional context retrieved)"}

## User Question
"{question}"

## Instructions
- Use the retrieved context to inform your interpretation
- Apply privacy-safe defaults (no customer/account IDs in output)
- Default to monthly trend if no time range specified
- Map business terms to the correct columns and filters
- If the question asks about a term defined in the context, use that definition

Return your analysis as JSON with the following structure:
{{
    "interpretation": "plain English description of what the user wants",
    "metrics": ["list of metrics to calculate"],
    "dimensions": ["list of dimensions to group by"],
    "filters": {{"column": "condition"}},
    "time_grain": "month/day/week/quarter",
    "privacy_note": "any privacy concerns or notes",
    "assumptions": ["assumptions made about ambiguous parts"],
    "confidence": "high/medium/low"
}}"""
    
    # Call LLM
    try:
        client = get_llm_client()
        response = client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True
        )
        
        # Parse response
        result = response.to_json()
        
        if result is None:
            result = {
                "interpretation": response.content,
                "parse_error": "Could not parse JSON response"
            }
        
        # Add metadata
        result["_tokens"] = response.usage
        result["_rag_metadata"] = rag_metadata
        
        return {"definition_result": result}
        
    except Exception as e:
        return {
            "definition_result": {
                "error": str(e),
                "interpretation": None
            }
        }


def get_definition_only(question: str) -> Dict[str, Any]:
    """
    Get definition for a question without full pipeline.
    
    Useful for testing or standalone use.
    
    Args:
        question: User question
        
    Returns:
        Definition result dict
    """
    result = run({"user_question": question})
    return result.get("definition_result", {})


if __name__ == "__main__":
    # Test the agent
    test_questions = [
        "What is net flow?",  # Should retrieve glossary definition
        "What's the total deposit amount by channel?",
        "Show me the monthly trend of withdrawals",
        "List top customers by transaction count",  # Should flag privacy concern
    ]
    
    print("Testing Definition Agent with RAG...\n")
    
    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"Question: {q}")
        print("="*60)
        
        result = run({"user_question": q})
        definition = result["definition_result"]
        
        print(f"Interpretation: {definition.get('interpretation', 'N/A')}")
        print(f"Metrics: {definition.get('metrics', 'N/A')}")
        print(f"Dimensions: {definition.get('dimensions', 'N/A')}")
        print(f"Privacy note: {definition.get('privacy_note', 'N/A')}")
        print(f"Confidence: {definition.get('confidence', 'N/A')}")
        
        # Show RAG metadata
        rag_meta = definition.get('_rag_metadata', {})
        print(f"\nRAG Retrieved: {rag_meta.get('total_knowledge', 0)} knowledge, {rag_meta.get('total_schema', 0)} schema chunks")
