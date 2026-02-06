#!/usr/bin/env python3
"""
Agentic Analytics Orchestrator - Main Entry Point

Run analytics queries using a multi-agent system.

Usage:
    python main.py "What is the total deposit amount by channel?"
    python main.py --interactive
    python main.py --history          # View query history
    python main.py --stats            # View performance statistics
"""

import sys
import argparse
from datetime import datetime

from src.orchestrator import run_query
from src.config import settings
from src.evaluation import (
    collect_feedback_interactive,
    get_query_store,
    format_feedback_summary,
    get_improvement_insights,
    score_to_stars,
    get_confidence_explanation,
    EvaluationResult
)


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


def run_single_query(question: str, verbose: bool = False, collect_feedback: bool = True):
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
    
    # Print metadata with self-evaluation
    print(f"\n📊 Stats:")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   Tokens: {result.get('total_tokens', 0)}")
    
    # Show confidence score
    self_scores = result.get("self_scores", {})
    if self_scores:
        overall = self_scores.get("overall", 0)
        confidence = result.get("confidence", "unknown")
        stars = score_to_stars(overall)
        print(f"   Confidence: {stars} ({overall:.0f}/100 - {confidence})")
        
        if verbose:
            print(f"\n   Score breakdown:")
            for key, value in self_scores.items():
                if key not in ("overall", "confidence", "issues"):
                    print(f"     • {key}: {value}")
            if self_scores.get("issues"):
                print(f"   Issues: {', '.join(self_scores['issues'])}")
    
    if result.get("errors"):
        print(f"\n⚠️ Errors:")
        for err in result["errors"]:
            print(f"   - {err}")
    
    # Collect user feedback (in interactive mode)
    session_id = result.get("session_id")
    if collect_feedback and session_id:
        collect_feedback_interactive(session_id)
    
    return result


def interactive_mode():
    """Run in interactive mode."""
    print_banner()
    print("Type your analytics questions. Type 'quit' or 'exit' to stop.")
    print("Commands: help, history, stats, quit\n")
    
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
            
            if question.lower() == "history":
                show_history()
                continue
            
            if question.lower() == "stats":
                show_stats()
                continue
            
            if question.lower() == "insights":
                show_insights()
                continue
            
            run_single_query(question, verbose=False, collect_feedback=True)
            
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

  Trends:
    - "Show me the monthly trend of deposits"
    - "How did withdrawals change over the last 3 months?"

  Comparisons:
    - "Compare digital vs branch transactions"
    - "Which channel has the highest deposit volume?"

Commands:
    help     - Show this help message
    history  - Show recent query history
    stats    - Show performance statistics
    insights - Show improvement insights
    quit     - Exit the program
""")


def show_history(limit: int = 10):
    """Show recent query history."""
    store = get_query_store()
    records = store.get_recent(limit=limit)
    
    if not records:
        print("\n📜 No query history found.")
        return
    
    print(f"\n📜 Recent Queries (last {len(records)}):")
    print("─" * 60)
    
    for i, record in enumerate(records, 1):
        # Truncate question
        q = record.question[:50] + "..." if len(record.question) > 50 else record.question
        
        # Format scores
        self_score = f"{record.self_score:.0f}" if record.self_score else "—"
        user_score = f"{'★' * record.user_score}{'☆' * (5 - record.user_score)}" if record.user_score else "unrated"
        
        # Format timestamp
        ts = record.created_at[:16].replace("T", " ")
        
        print(f"{i}. [{ts}] {q}")
        print(f"   Self: {self_score}/100 | User: {user_score} | Tokens: {record.total_tokens}")
        if record.error_count > 0:
            print(f"   ⚠️ {record.error_count} error(s)")
        print()


def show_stats():
    """Show performance statistics."""
    print("\n" + format_feedback_summary())
    
    store = get_query_store()
    stats = store.get_stats()
    
    print("\n📈 Performance Metrics:")
    print("─" * 30)
    if stats.get("avg_latency_ms"):
        print(f"Avg latency:       {stats['avg_latency_ms']:.0f}ms")
    if stats.get("avg_tokens"):
        print(f"Avg tokens/query:  {stats['avg_tokens']:.0f}")
    if stats.get("error_rate") is not None:
        print(f"Error rate:        {stats['error_rate']:.1f}%")


def show_insights():
    """Show improvement insights based on feedback."""
    print("\n💡 Improvement Insights:")
    print("─" * 30)
    
    insights = get_improvement_insights()
    
    if not insights:
        print("No insights available yet. Rate more queries to get insights!")
        return
    
    for insight in insights:
        print(insight)


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
    parser.add_argument(
        "--history",
        action="store_true",
        help="Show recent query history"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show performance statistics"
    )
    parser.add_argument(
        "--insights",
        action="store_true",
        help="Show improvement insights"
    )
    parser.add_argument(
        "--no-feedback",
        action="store_true",
        help="Skip feedback collection after query"
    )
    
    args = parser.parse_args()
    
    # Handle history/stats commands (don't require API key)
    if args.history:
        show_history()
        return
    
    if args.stats:
        show_stats()
        return
    
    if args.insights:
        show_insights()
        return
    
    # Validate settings for query mode
    valid, msg = settings.validate()
    if not valid:
        print(f"❌ Configuration error: {msg}")
        sys.exit(1)
    
    if args.interactive or args.question is None:
        interactive_mode()
    else:
        run_single_query(
            args.question, 
            verbose=args.verbose, 
            collect_feedback=not args.no_feedback
        )


if __name__ == "__main__":
    main()
