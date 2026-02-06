"""
Prompt Loader: Centralized prompt management and composition.

Loads prompts from /prompts folder and composes them for agents.
"""

from pathlib import Path
from functools import lru_cache
from typing import Optional, Dict

from src.config.settings import settings


# Prompt directory
PROMPTS_DIR = settings.project_root / "prompts"


@lru_cache(maxsize=20)
def load_prompt(path: str) -> str:
    """
    Load a prompt file from the prompts directory.
    
    Args:
        path: Relative path within prompts/ (e.g., "system.md", "agents/sql.md")
        
    Returns:
        Content of the prompt file
    """
    full_path = PROMPTS_DIR / path
    
    if not full_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {full_path}")
    
    return full_path.read_text()


def get_system_prompt() -> str:
    """Get the global system prompt."""
    return load_prompt("system.md")


def get_schema_context() -> str:
    """Get the schema context prompt."""
    return load_prompt("schema_context.md")


def get_scope_guardrail() -> str:
    """Get the scope guardrail prompt."""
    return load_prompt("guardrails/scope.md")


def get_sql_safety_guardrail() -> str:
    """Get the SQL safety guardrail prompt."""
    return load_prompt("guardrails/sql_safety.md")


def get_agent_prompt(agent_name: str) -> str:
    """
    Get an agent-specific prompt.
    
    Args:
        agent_name: One of: definition, sql, quality, explanation
    """
    return load_prompt(f"agents/{agent_name}.md")


def compose_agent_prompt(
    agent_name: str,
    include_system: bool = True,
    include_schema: bool = True,
    include_guardrails: bool = False,
    extra_context: Optional[str] = None
) -> str:
    """
    Compose a full prompt for an agent by combining multiple prompt files.
    
    Args:
        agent_name: The agent to compose for
        include_system: Include global system prompt
        include_schema: Include schema context
        include_guardrails: Include guardrail prompts
        extra_context: Additional context to append
        
    Returns:
        Composed prompt string
    """
    parts = []
    
    # Global system prompt
    if include_system:
        parts.append(get_system_prompt())
    
    # Schema context
    if include_schema:
        parts.append(get_schema_context())
    
    # Guardrails (for scope-sensitive agents)
    if include_guardrails:
        if agent_name in ("definition", "sql"):
            parts.append(get_sql_safety_guardrail())
    
    # Agent-specific prompt
    parts.append(get_agent_prompt(agent_name))
    
    # Extra context
    if extra_context:
        parts.append(extra_context)
    
    return "\n\n---\n\n".join(parts)


def compose_scope_check_prompt() -> str:
    """
    Compose prompt for scope checking (used by scope guardrail).
    """
    parts = [
        get_system_prompt(),
        get_scope_guardrail()
    ]
    return "\n\n---\n\n".join(parts)


def compose_sql_validation_prompt() -> str:
    """
    Compose prompt for SQL validation (used by SQL guardrail).
    """
    parts = [
        get_schema_context(),
        get_sql_safety_guardrail()
    ]
    return "\n\n---\n\n".join(parts)


# Pre-composed prompts for common use cases
class AgentPrompts:
    """Pre-composed prompts for each agent."""
    
    @staticmethod
    @lru_cache(maxsize=1)
    def definition() -> str:
        """Full prompt for Definition Agent."""
        return compose_agent_prompt(
            "definition",
            include_system=True,
            include_schema=True,
            include_guardrails=False
        )
    
    @staticmethod
    @lru_cache(maxsize=1)
    def sql() -> str:
        """Full prompt for SQL Agent."""
        return compose_agent_prompt(
            "sql",
            include_system=True,
            include_schema=True,
            include_guardrails=True
        )
    
    @staticmethod
    @lru_cache(maxsize=1)
    def quality() -> str:
        """Full prompt for Data Quality Agent."""
        return compose_agent_prompt(
            "quality",
            include_system=True,
            include_schema=False,  # Doesn't need full schema
            include_guardrails=False
        )
    
    @staticmethod
    @lru_cache(maxsize=1)
    def explanation() -> str:
        """Full prompt for Explanation Agent."""
        return compose_agent_prompt(
            "explanation",
            include_system=True,
            include_schema=False,
            include_guardrails=False
        )


# Privacy constants
# Note: Set to 5 for demo dataset (which has ~6-8 accounts per product/month)
# In production, use 10 or higher for stronger privacy guarantees
PRIVACY_THRESHOLD = 5  # Minimum distinct entities for k-anonymity


def get_privacy_rules() -> Dict:
    """Get privacy configuration."""
    return {
        "k_anonymity_threshold": PRIVACY_THRESHOLD,
        "forbidden_output_columns": ["customer_id", "account_id"],
        "max_result_rows": 200,
        "require_aggregation": True
    }


if __name__ == "__main__":
    # Test prompt loading
    print("=== Testing Prompt Loader ===\n")
    
    print("System prompt loaded:", len(get_system_prompt()), "chars")
    print("Schema context loaded:", len(get_schema_context()), "chars")
    print("Scope guardrail loaded:", len(get_scope_guardrail()), "chars")
    print("SQL safety loaded:", len(get_sql_safety_guardrail()), "chars")
    
    print("\n=== Composed Agent Prompts ===\n")
    
    for agent in ["definition", "sql", "quality", "explanation"]:
        prompt = compose_agent_prompt(agent)
        print(f"{agent}: {len(prompt)} chars")
    
    print("\n=== Privacy Rules ===")
    print(get_privacy_rules())
