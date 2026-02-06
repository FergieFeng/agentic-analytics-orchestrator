#!/usr/bin/env python3
"""
Scaffold Agent: Generate a new specialist agent folder structure.

Usage:
    python src/apps/scaffold_agent.py --name "new_agent"
    python src/apps/scaffold_agent.py --name "campaign_agent" --description "Campaign analytics"
"""

import argparse
import os
from pathlib import Path


AGENT_TEMPLATE = '''"""
{name_title} Agent: {description}

Responsibilities:
- TODO: Define responsibilities
"""

from typing import Optional
from src.orchestrator.state import OrchestratorState


def run(state: OrchestratorState) -> dict:
    """
    Execute the {name_title} Agent.
    
    Args:
        state: Current orchestrator state
        
    Returns:
        dict with results to merge into state
    """
    
    # TODO: Implement agent logic
    
    result = {{
        "status": "success",
        "data": None
    }}
    
    return {{"{name}_result": result}}
'''


PROMPT_TEMPLATE = '''# {name_title} Agent Prompt

You are the {name_title} Agent. Your job is to {description}.

## Input

- User question from orchestrator
- Previous agent results (if any)

## Output

Return structured results for the orchestrator.

## Guidelines

- TODO: Add specific guidelines for this agent
'''


INIT_TEMPLATE = '''# {name_title} Agent
from .agent import run

__all__ = ["run"]
'''


def create_agent(name: str, description: str = "TODO: Add description"):
    """Create a new agent folder structure."""
    
    # Normalize name
    name_lower = name.lower().replace(" ", "_")
    name_title = name.replace("_", " ").title()
    
    # Create folder
    agent_dir = Path(f"src/specialists/{name_lower}")
    
    if agent_dir.exists():
        print(f"Error: Agent folder already exists: {agent_dir}")
        return False
    
    agent_dir.mkdir(parents=True)
    
    # Create __init__.py
    init_content = INIT_TEMPLATE.format(name_title=name_title)
    (agent_dir / "__init__.py").write_text(init_content)
    
    # Create agent.py
    agent_content = AGENT_TEMPLATE.format(
        name=name_lower,
        name_title=name_title,
        description=description
    )
    (agent_dir / "agent.py").write_text(agent_content)
    
    # Create prompt.md
    prompt_content = PROMPT_TEMPLATE.format(
        name_title=name_title,
        description=description
    )
    (agent_dir / "prompt.md").write_text(prompt_content)
    
    print(f"Created agent: {agent_dir}")
    print(f"  - __init__.py")
    print(f"  - agent.py")
    print(f"  - prompt.md")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new specialist agent")
    parser.add_argument("--name", required=True, help="Agent name (e.g., 'campaign_agent')")
    parser.add_argument("--description", default="TODO: Add description", help="Agent description")
    
    args = parser.parse_args()
    create_agent(args.name, args.description)


if __name__ == "__main__":
    main()
