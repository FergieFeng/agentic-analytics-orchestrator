"""
Schema Tool: Retrieve table schema and domain knowledge.

Provides context for agents to understand available columns and business metrics.
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from functools import lru_cache

from src.config.settings import settings


@lru_cache(maxsize=1)
def load_schema() -> Dict[str, Any]:
    """
    Load schema definition from JSON file.
    
    Returns:
        Schema dict with columns, enums, and notes
    """
    schema_path = settings.get_absolute_path(settings.schema_path)
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(schema_path) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_knowledge() -> Dict[str, Any]:
    """
    Load domain knowledge from JSON file.
    
    Returns:
        Knowledge dict with glossary, metrics, and SQL patterns
    """
    knowledge_path = settings.get_absolute_path(settings.knowledge_path)
    
    if not knowledge_path.exists():
        raise FileNotFoundError(f"Knowledge file not found: {knowledge_path}")
    
    with open(knowledge_path) as f:
        return json.load(f)


def get_column_names() -> List[str]:
    """Get list of all column names."""
    schema = load_schema()
    return [col["name"] for col in schema["columns"]]


def get_column_info(column_name: str) -> Optional[Dict]:
    """
    Get detailed info for a specific column.
    
    Args:
        column_name: Name of the column
        
    Returns:
        Dict with name, type, description, and enum values if applicable
    """
    schema = load_schema()
    
    for col in schema["columns"]:
        if col["name"] == column_name:
            result = col.copy()
            
            # Add enum values if this column has them
            if "enum" in col:
                result["enum_values"] = col["enum"]
            elif column_name in schema.get("enums", {}):
                result["enum_details"] = schema["enums"][column_name]
            
            return result
    
    return None


def get_enum_values(enum_name: str) -> Optional[Dict]:
    """
    Get enum values and descriptions.
    
    Args:
        enum_name: Name of the enum (e.g., 'product_type', 'channel')
        
    Returns:
        Dict mapping enum values to descriptions
    """
    schema = load_schema()
    return schema.get("enums", {}).get(enum_name)


def get_metrics(category: Optional[str] = None) -> List[Dict]:
    """
    Get metric definitions.
    
    Args:
        category: Optional category filter (volume, customer, channel, fee)
        
    Returns:
        List of metric definitions with name, definition, and SQL
    """
    knowledge = load_knowledge()
    metrics = knowledge.get("metrics", {})
    
    if category:
        return metrics.get(category, [])
    
    # Return all metrics flattened
    all_metrics = []
    for cat, metric_list in metrics.items():
        for metric in metric_list:
            metric_with_cat = metric.copy()
            metric_with_cat["category"] = cat
            all_metrics.append(metric_with_cat)
    
    return all_metrics


def get_sql_pattern(pattern_name: str) -> Optional[Dict]:
    """
    Get a predefined SQL pattern.
    
    Args:
        pattern_name: Name of the pattern (e.g., 'daily_summary', 'channel_analysis')
        
    Returns:
        Dict with description and SQL template
    """
    knowledge = load_knowledge()
    return knowledge.get("sql_patterns", {}).get(pattern_name)


def get_business_rules() -> List[str]:
    """Get list of business rules."""
    knowledge = load_knowledge()
    return knowledge.get("business_rules", [])


def get_glossary() -> Dict[str, Dict[str, str]]:
    """Get business glossary with terms and definitions."""
    knowledge = load_knowledge()
    return knowledge.get("glossary", {})


def get_schema_context() -> str:
    """
    Get formatted schema context for LLM prompts.
    
    Returns:
        Formatted string with table schema and key info
    """
    schema = load_schema()
    knowledge = load_knowledge()
    
    lines = [
        f"## Table: {schema['table_name']}",
        f"{schema['description']}",
        "",
        "### Columns:",
    ]
    
    for col in schema["columns"]:
        enum_note = ""
        if "enum" in col:
            enum_note = f" (values: {', '.join(col['enum'])})"
        lines.append(f"- `{col['name']}` ({col['type']}): {col['description']}{enum_note}")
    
    lines.extend([
        "",
        "### Business Rules:",
    ])
    
    for rule in knowledge.get("business_rules", []):
        lines.append(f"- {rule}")
    
    return "\n".join(lines)


def get_metrics_context() -> str:
    """
    Get formatted metrics context for LLM prompts.
    
    Returns:
        Formatted string with metric definitions
    """
    metrics = get_metrics()
    
    lines = ["## Available Metrics:"]
    
    for metric in metrics:
        lines.append(f"- **{metric['name']}**: {metric['definition']}")
        lines.append(f"  SQL: `{metric['sql']}`")
    
    return "\n".join(lines)


if __name__ == "__main__":
    print("=== Schema Context ===")
    print(get_schema_context())
    print()
    
    print("=== Metrics Context ===")
    print(get_metrics_context())
    print()
    
    print("=== Column Names ===")
    print(get_column_names())
