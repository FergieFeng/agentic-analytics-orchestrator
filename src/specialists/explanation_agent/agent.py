"""
Explanation Agent: Generates business insights from query results.

Responsibilities:
- Synthesize results into plain English
- Highlight key insights and trends
- Provide business context
"""

import json
from typing import Dict, Any, List
from pathlib import Path

from src.config.llm import get_llm_client
from src.tools.schema_tool import get_glossary, get_business_rules


SYSTEM_PROMPT = """You are the Explanation Agent for a banking analytics system.

Your job is to explain query results in clear, business-friendly language.

## Business Context

{business_rules}

## Your Task

Given:
1. The original question
2. The SQL query that was run
3. The query results
4. Data quality notes

Generate a clear, concise explanation that:
1. Directly answers the user's question
2. Highlights key insights from the data
3. Notes any important caveats or limitations
4. Suggests follow-up questions if relevant

## Output Format

Return a JSON object:
```json
{{
  "summary": "One sentence answer to the question",
  "insights": ["Key insight 1", "Key insight 2"],
  "caveats": ["Any data limitations or notes"],
  "follow_up_questions": ["Suggested follow-up question"]
}}
```

## Style Guidelines

- Be concise but informative
- Use business terminology appropriately
- Format numbers clearly (e.g., "$45,230" not "45230.00")
- Compare to benchmarks or trends when possible
- Don't just repeat the data - interpret it"""


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the Explanation Agent.
    
    Args:
        state: Current state with question, sql_result, and quality_result
        
    Returns:
        dict with explanation containing summary, insights, and follow-ups
    """
    question = state.get("user_question", "")
    sql_query = state.get("sql_query", "")
    sql_result = state.get("sql_result", {})
    quality_result = state.get("quality_result", {})
    sql_explanation = state.get("sql_explanation", "")
    
    # Handle missing results
    if not sql_result or not sql_result.get("data"):
        return {
            "explanation": {
                "summary": "Unable to generate results for this question.",
                "insights": [],
                "caveats": ["The query returned no data or encountered an error."],
                "follow_up_questions": ["Try rephrasing your question or checking the date range."]
            }
        }
    
    # Build context
    business_rules = get_business_rules()
    rules_text = "\n".join(f"- {rule}" for rule in business_rules)
    
    system_prompt = SYSTEM_PROMPT.format(business_rules=rules_text)
    
    # Format result data for the prompt
    data = sql_result.get("data", [])
    row_count = sql_result.get("row_count", 0)
    
    # Limit data shown to LLM
    data_preview = data[:20] if len(data) > 20 else data
    
    user_prompt = f"""Explain these query results:

**Original Question:** "{question}"

**SQL Query:** 
```sql
{sql_query}
```

**Query Explanation:** {sql_explanation}

**Results ({row_count} rows):**
```json
{json.dumps(data_preview, indent=2, default=str)}
```

**Data Quality:** {quality_result.get('status', 'unknown')} - {quality_result.get('message', '')}

Generate a business-friendly explanation as JSON."""
    
    try:
        client = get_llm_client()
        response = client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True
        )
        
        result = response.to_json()
        
        if result is None:
            result = {
                "summary": response.content,
                "insights": [],
                "caveats": [],
                "follow_up_questions": []
            }
        
        result["_tokens"] = response.usage
        
        return {"explanation": result}
        
    except Exception as e:
        return {
            "explanation": {
                "summary": f"Error generating explanation: {str(e)}",
                "insights": [],
                "caveats": ["An error occurred while processing results."],
                "follow_up_questions": []
            }
        }


def format_answer(state: Dict[str, Any]) -> str:
    """
    Format the final answer for display to the user.
    
    Args:
        state: Complete state with all results
        
    Returns:
        Formatted string answer
    """
    explanation = state.get("explanation") or {}
    sql_result = state.get("sql_result") or {}
    quality_result = state.get("quality_result") or {}
    
    lines = []
    
    # Summary
    summary = explanation.get("summary", "No summary available.")
    lines.append(f"**Answer:** {summary}")
    lines.append("")
    
    # Insights
    insights = explanation.get("insights", [])
    if insights:
        lines.append("**Key Insights:**")
        for insight in insights:
            lines.append(f"- {insight}")
        lines.append("")
    
    # Data table (if small)
    data = sql_result.get("data", [])
    if data and len(data) <= 10:
        lines.append("**Data:**")
        # Simple markdown table
        if data:
            cols = list(data[0].keys())
            lines.append("| " + " | ".join(cols) + " |")
            lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
            for row in data:
                values = [str(row.get(c, "")) for c in cols]
                lines.append("| " + " | ".join(values) + " |")
            lines.append("")
    
    # Caveats
    caveats = explanation.get("caveats", [])
    if caveats:
        lines.append("**Notes:**")
        for caveat in caveats:
            lines.append(f"- {caveat}")
        lines.append("")
    
    # Quality warnings
    if quality_result.get("status") == "warning":
        warnings = [c["message"] for c in quality_result.get("checks", []) if c["status"] == "warning"]
        if warnings:
            lines.append("**Data Quality Warnings:**")
            for w in warnings:
                lines.append(f"- ⚠️ {w}")
            lines.append("")
    
    # Follow-up questions
    follow_ups = explanation.get("follow_up_questions", [])
    if follow_ups:
        lines.append("**You might also ask:**")
        for q in follow_ups:
            lines.append(f"- {q}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test the agent
    test_state = {
        "user_question": "What's the total deposit amount by channel?",
        "sql_query": "SELECT channel, SUM(event_amount) as total FROM events WHERE event_amount > 0 GROUP BY channel",
        "sql_explanation": "Aggregates positive event amounts by channel",
        "sql_result": {
            "data": [
                {"channel": "DIGITAL", "total": 95000.50},
                {"channel": "BRANCH", "total": 45000.00},
                {"channel": "BATCH", "total": 12000.25}
            ],
            "columns": ["channel", "total"],
            "row_count": 3
        },
        "quality_result": {
            "status": "pass",
            "message": "All checks passed"
        }
    }
    
    print("Testing Explanation Agent...")
    print(f"Question: {test_state['user_question']}")
    print()
    
    result = run(test_state)
    
    print("Explanation:")
    print(json.dumps(result["explanation"], indent=2))
    print()
    
    print("Formatted Answer:")
    print(format_answer({**test_state, **result}))
