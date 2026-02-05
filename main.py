#!/usr/bin/env python3
"""
Agentic Analytics Orchestrator - Main Entry Point

Run analytics queries using a multi-agent system.

Usage:
    python main.py "What is the total deposit amount by channel?"
    python main.py --interactive
"""

import sys
import argparse
from datetime import datetime

from src.orchestrator import run_query
from src.config import settings


def print_banner():
    """Print the application banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║          Agentic Analytics Orchestrator                       ║
║          Multi-Agent Banking Analytics System                 ║
╚═══════════════════════════════════════════════════════════════╝
""")


def print_trace(state: dict, verbose: bool = False):
    """Print execution trace."""
    trace = state.get("trace", [])
    
    if not trace:
        return
    
    print("\n--- Execution Trace ---")
    for entry in trace:
        agent = entry.get("agent", "unknown")
        action = entry.get("action", "")
        details = entry.get("details", {})
        
        if action == "started":
            print(f"  → {agent}: starting...")
        elif action == "completed":
            detail_str = ""
            if verbose and details:
                detail_str = f" ({details})"
            print(f"  ✓ {agent}: completed{detail_str}")
        elif action == "checked":
            status = details.get("status", "unknown")
            print(f"  ○ {agent}: {status}")
        elif action == "routed":
            agents = details.get("agents", [])
            print(f"  ○ {agent}: → {', '.join(agents)}")


def run_single_query(question: str, verbose: bool = False):
    """Run a single query and display results."""
    print(f"\n🔍 Question: {question}\n")
    print("Processing...")
    
    start = datetime.now()
    result = run_query(question)
    elapsed = (datetime.now() - start).total_seconds()
    
    # Print trace if verbose
    if verbose:
        print_trace(result, verbose=True)
    
    # Print final response
    print("\n" + "="*60)
    print(result.get("final_response", "No response generated."))
    print("="*60)
    
    # Print metadata
    print(f"\n📊 Stats:")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   Tokens: {result.get('total_tokens', 0)}")
    
    if result.get("errors"):
        print(f"\n⚠️ Errors:")
        for err in result["errors"]:
            print(f"   - {err}")
    
    return result


def interactive_mode():
    """Run in interactive mode."""
    print_banner()
    print("Type your analytics questions. Type 'quit' or 'exit' to stop.\n")
    
    while True:
        try:
            question = input("\n💬 Your question: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ("quit", "exit", "q"):
                print("\nGoodbye! 👋")
                break
            
            if question.lower() == "help":
                print_help()
                continue
            
            run_single_query(question, verbose=False)
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def print_help():
    """Print help message."""
    print("""
📖 Help - Example Questions:

  Aggregations:
    - "What is the total deposit amount?"
    - "How many transactions were there last month?"
    - "What's the average withdrawal amount?"

  Breakdowns:
    - "Show me deposits by channel"
    - "What's the transaction count by product type?"
    - "List top 10 customers by transaction volume"

  Trends:
    - "Show me the monthly trend of deposits"
    - "How did withdrawals change over the last 3 months?"

  Comparisons:
    - "Compare digital vs branch transactions"
    - "Which channel has the highest deposit volume?"

Commands:
    help  - Show this help message
    quit  - Exit the program
""")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agentic Analytics Orchestrator - Multi-Agent Banking Analytics"
    )
    parser.add_argument(
        "question",
        nargs="?",
        help="Analytics question to answer"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed execution trace"
    )
    
    args = parser.parse_args()
    
    # Validate settings
    valid, msg = settings.validate()
    if not valid:
        print(f"❌ Configuration error: {msg}")
        sys.exit(1)
    
    if args.interactive or args.question is None:
        interactive_mode()
    else:
        run_single_query(args.question, verbose=args.verbose)


if __name__ == "__main__":
    main()
