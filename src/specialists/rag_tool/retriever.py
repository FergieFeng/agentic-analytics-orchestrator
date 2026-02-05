"""
RAG Retriever: Lightweight retrieval for knowledge grounding.

Responsibilities:
- Retrieve relevant schema information
- Fetch metric definitions
- Provide context for ambiguous terms
"""

from typing import List, Optional


def retrieve(query: str, top_k: int = 3) -> List[dict]:
    """
    Retrieve relevant context for a query.
    
    Args:
        query: Search query (user question or term)
        top_k: Number of results to return
        
    Returns:
        List of relevant documents/context
    """
    
    # TODO: Implement retrieval
    # Options:
    # 1. Simple keyword search in schema.json
    # 2. Vector similarity search (Phase 3)
    # 3. Hybrid approach
    
    # Placeholder - return schema info
    return [
        {
            "type": "schema",
            "content": "sample_events table contains banking transaction events",
            "relevance": 0.9
        }
    ]


def get_schema_context() -> str:
    """Return schema information as context string."""
    
    # TODO: Load from config/schema.json
    return """
    Table: sample_events
    Columns: event_id, event_ts, event_date, account_id, customer_id, 
             product_type, event_type, event_name, channel, 
             event_amount, currency, balance_after
    """
