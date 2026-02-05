"""
Definition Agent: Interprets metrics, dimensions, and analytical intent.

Responsibilities:
- Parse user questions to identify requested metrics
- Map business terms to table columns
- Clarify ambiguous requests
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path

from src.config.llm import get_llm_client
from src.tools.schema_tool import get_schema_context, get_metrics_context, load_knowledge


SYSTEM_PROMPT = """You are the Definition Agent for a banking analytics system.

Your job is to interpret user questions and extract structured analytical definitions.

{schema_context}

{metrics_context}

## Your Task

Given a user question, extract:
1. **metric**: What to measure (e.g., SUM of event_amount, COUNT of events)
2. **dimensions**: How to group results (e.g., by channel, by month)
3. **filters**: Conditions to apply (e.g., only deposits, specific date range)
4. **time_range**: Date constraints if mentioned
5. **interpretation**: Plain English summary of what the user wants

## Output Format

Return a JSON object:
```json
{{
  "metric": {{
    "function": "SUM|COUNT|AVG|MIN|MAX",
    "column": "column_name",
    "alias": "result_name"
  }},
  "dimensions": ["column1", "column2"],
  "filters": [
    {{"column": "col", "operator": "=|>|<|>=|<=|IN|LIKE", "value": "val"}}
  ],
  "time_range": {{
    "start": "YYYY-MM-DD or null",
    "end": "YYYY-MM-DD or null",
    "period": "last_month|this_month|last_week|etc or null"
  }},
  "interpretation": "Plain English description"
}}
```

## Important Rules

1. Map business terms to correct columns:
   - "deposits" → event_amount > 0 AND event_type = 'money_movement'
   - "withdrawals" → event_amount < 0 AND event_type = 'money_movement'
   - "fees" → event_type = 'fee'
   - "transactions" → event_type = 'money_movement'

2. For time-based questions without specific dates, use relative periods
3. Always include an interpretation that explains your understanding
4. If the question is ambiguous, make reasonable assumptions and note them"""


def load_prompt() -> str:
    """Load the prompt template from prompt.md."""
    prompt_path = Path(__file__).parent / "prompt.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the Definition Agent.
    
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
    
    # Build context
    schema_context = get_schema_context()
    metrics_context = get_metrics_context()
    
    system_prompt = SYSTEM_PROMPT.format(
        schema_context=schema_context,
        metrics_context=metrics_context
    )
    
    user_prompt = f"""Analyze this question and provide a structured definition:

Question: "{question}"

Return your analysis as JSON."""
    
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
            # Try to extract from content
            result = {
                "interpretation": response.content,
                "parse_error": "Could not parse JSON response"
            }
        
        # Add metadata
        result["_tokens"] = response.usage
        
        return {"definition_result": result}
        
    except Exception as e:
        return {
            "definition_result": {
                "error": str(e),
                "interpretation": None
            }
        }


if __name__ == "__main__":
    # Test the agent
    test_questions = [
        "What's the total deposit amount by channel?",
        "Show me the monthly trend of withdrawals",
        "How many transactions did digital customers make?",
    ]
    
    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"Question: {q}")
        print("="*60)
        
        result = run({"user_question": q})
        definition = result["definition_result"]
        
        print(f"Interpretation: {definition.get('interpretation', 'N/A')}")
        print(f"Metric: {definition.get('metric', 'N/A')}")
        print(f"Dimensions: {definition.get('dimensions', [])}")
        print(f"Filters: {definition.get('filters', [])}")
