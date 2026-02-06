"""
Explanation Agent: Generates business insights from query results.

Responsibilities:
- Synthesize results into plain English
- Highlight key insights and trends
- Document assumptions made
- Provide business context
- Note any privacy suppressions
"""

import json
from typing import Dict, Any, List
from pathlib import Path

from src.config.llm import get_llm_client
from src.config.prompts import AgentPrompts


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
    sql_result = state.get("sql_result") or {}
    quality_result = state.get("quality_result") or {}
    sql_explanation = state.get("sql_explanation", "")
    
    # Handle missing results
    if not sql_result or not sql_result.get("data"):
        # Check if this is due to privacy filtering
        has_data_check = next(
            (c for c in quality_result.get("checks", []) if c.get("name") == "has_data"),
            {}
        )
        likely_cause = has_data_check.get("details", {}).get("likely_cause", "")
        
        if likely_cause == "k_anonymity_filter":
            return {
                "explanation": {
                    "summary": "This breakdown cannot be shown due to privacy protection requirements.",
                    "insights": [
                        "The requested data exists but involves too few accounts to report safely.",
                        "Our privacy policy requires at least 5 distinct accounts per data bucket."
                    ],
                    "caveats": [
                        "Some data was suppressed to protect individual privacy.",
                        "This is not an error - it's a privacy safeguard."
                    ],
                    "assumptions": [],
                    "follow_up_questions": [
                        "Try a broader aggregation (e.g., quarterly totals instead of monthly)",
                        "Ask for overall totals without dimensional breakdowns",
                        "Combine with other categories that have more data"
                    ]
                }
            }
        
        return {
            "explanation": {
                "summary": "Unable to generate results for this question.",
                "insights": [],
                "caveats": ["The query returned no data or encountered an error."],
                "assumptions": [],
                "follow_up_questions": ["Try rephrasing your question or checking the date range."]
            }
        }
    
    # Get composed prompt
    system_prompt = AgentPrompts.explanation()
    
    # Format result data for the prompt
    data = sql_result.get("data", [])
    row_count = sql_result.get("row_count", 0)
    
    # Limit data shown to LLM
    data_preview = data[:20] if len(data) > 20 else data
    
    # Privacy compliance info
    privacy_info = quality_result.get("privacy_compliance", {})
    privacy_note = ""
    if privacy_info.get("concerns"):
        privacy_note = f"\n\nPrivacy notes: {privacy_info['concerns']}"
    
    user_prompt = f"""Explain these query results in business-friendly language.

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
{privacy_note}

Remember:
- Never mention specific customer or account IDs
- Note any assumptions made (time range, metric definitions)
- If any data was suppressed for privacy, mention it
- Format numbers clearly with commas (e.g., 18,504)
- IMPORTANT: Do NOT use $ for currency - use "USD" or just the number ($ breaks markdown rendering)

Generate a business-friendly explanation as JSON with: summary, insights, caveats, assumptions, follow_up_questions"""
    
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
                "assumptions": [],
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
                "assumptions": [],
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
    
    # Data table (if small and appropriate)
    data = sql_result.get("data", [])
    if data and len(data) <= 10:
        lines.append("**Data:**")
        if data:
            cols = list(data[0].keys())
            
            # Sort by date/month column if present (ascending)
            date_cols = [c for c in cols if c in ('month', 'date', 'event_date', 'year', 'quarter', 'week')]
            if date_cols:
                sort_col = date_cols[0]
                data = sorted(data, key=lambda x: str(x.get(sort_col, '')))
            
            lines.append("| " + " | ".join(cols) + " |")
            lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
            for row in data:
                values = [str(row.get(c, "")) for c in cols]
                lines.append("| " + " | ".join(values) + " |")
            lines.append("")
    
    # Assumptions
    assumptions = explanation.get("assumptions", [])
    if assumptions:
        lines.append("**Assumptions:**")
        for assumption in assumptions:
            lines.append(f"- {assumption}")
        lines.append("")
    
    # Caveats
    caveats = explanation.get("caveats", [])
    if caveats:
        lines.append("**Notes:**")
        for caveat in caveats:
            lines.append(f"- {caveat}")
        lines.append("")
    
    # Privacy warnings
    privacy_compliance = quality_result.get("privacy_compliance", {})
    if privacy_compliance.get("concerns"):
        lines.append("**Privacy Notes:**")
        lines.append("- Some breakdowns may be suppressed due to privacy thresholds")
        lines.append("")
    
    # Quality warnings
    if quality_result.get("status") == "warning":
        warnings = [c["message"] for c in quality_result.get("checks", []) 
                   if c["status"] == "warning" and "privacy" not in c["name"].lower()]
        if warnings:
            lines.append("**Data Quality Notes:**")
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
            ],
            "columns": ["channel", "total"],
            "row_count": 2
        },
        "quality_result": {
            "status": "pass",
            "message": "All checks passed",
            "privacy_compliance": {"k_anonymity_met": True, "concerns": []}
        }
    }
    
    print("Testing Explanation Agent...")
    
    result = run(test_state)
    
    print("\nFormatted Answer:")
    print(format_answer({**test_state, **result}))
