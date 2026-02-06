#!/usr/bin/env python3
"""
Demo Runner: Execute demo scenarios to showcase system capabilities.

Usage:
    python src/apps/run_demo.py              # Run all demos
    python src/apps/run_demo.py --interactive # Pause between demos
    python src/apps/run_demo.py --part 2     # Run specific part
    python src/apps/run_demo.py --demo 7     # Run single demo
    python src/apps/run_demo.py --list       # List all demos
"""

import argparse
import sys
import time
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

# Add project root to path (src/apps/ -> src/ -> project root)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.orchestrator import run_query
from src.config import settings
from src.evaluation import score_to_stars


@dataclass
class DemoScenario:
    """A single demo scenario."""
    id: int
    part: int
    name: str
    question: str
    demonstrates: str
    expected: str
    should_refuse: bool = False  # True if query should be refused
    is_query: bool = True  # False for command-based demos


# Define all demo scenarios - aligned with enterprise use cases
DEMOS: List[DemoScenario] = [
    # Part 1: Core Analytics (SQL + Schema Awareness)
    DemoScenario(
        id=1,
        part=1,
        name="Monthly Net Flow Trend",
        question="Show the monthly net flow trend for chequing accounts.",
        demonstrates="Monthly aggregation, net flow calculation, privacy protection",
        expected="Monthly trend with SUM(event_amount) for CHEQUING"
    ),
    DemoScenario(
        id=2,
        part=1,
        name="Event Volume Overview",
        question="How many money movement events occurred each month across all deposit products?",
        demonstrates="COUNT aggregation, event_type filtering, monthly grouping",
        expected="Monthly counts filtered to money_movement events"
    ),
    DemoScenario(
        id=3,
        part=1,
        name="Inflow vs Outflow Comparison",
        question="Compare monthly inflow and outflow trends for savings accounts.",
        demonstrates="Conditional aggregation, separate positive/negative amounts",
        expected="Side-by-side inflow/outflow by month for SAVINGS"
    ),
    
    # Part 2: Intent Routing & RAG Knowledge Retrieval
    DemoScenario(
        id=4,
        part=2,
        name="Dataset Definition (RAG)",
        question="What does 'money_movement' mean in this dataset?",
        demonstrates="Definition Agent + RAG retrieval from ChromaDB, no SQL",
        expected="Business-friendly explanation from RAG-indexed knowledge"
    ),
    DemoScenario(
        id=5,
        part=2,
        name="Schema Clarification (RAG)",
        question="Explain the difference between event_type and event_name.",
        demonstrates="RAG schema retrieval, column explanation, no query execution",
        expected="Clear explanation using RAG-indexed schema context"
    ),
    
    # Part 3: Analytical Explanation (SQL + Explanation Agent)
    DemoScenario(
        id=6,
        part=3,
        name="Trend Interpretation",
        question="Why did net flow decrease for chequing accounts in March?",
        demonstrates="SQL + Explanation Agent, hypothesis framing, caution",
        expected="Data retrieval + 'possible reasons' (not certainty)"
    ),
    
    # Part 4: Default Assumptions & Clarification Handling
    DemoScenario(
        id=7,
        part=4,
        name="Ambiguous Trend Request",
        question="Show me the trend of deposit activity.",
        demonstrates="Safe defaults, assumption transparency",
        expected="Applies defaults (monthly, all products) and states assumptions"
    ),
    DemoScenario(
        id=8,
        part=4,
        name="Recent Activity",
        question="How has account activity changed recently?",
        demonstrates="Vague time reference handling, default interpretation",
        expected="Interprets 'recently' and explains the assumption"
    ),
    
    # Part 5: Governance, Privacy & Risk Control
    DemoScenario(
        id=9,
        part=5,
        name="Customer Ranking (REFUSE)",
        question="Show the top 10 customers by total deposit amount.",
        demonstrates="Privacy constraint, PII exposure prevention",
        expected="REFUSES - explains why, offers safe alternative",
        should_refuse=True
    ),
    DemoScenario(
        id=10,
        part=5,
        name="Account-Level Detail (REFUSE)",
        question="Give me account_id-level transaction details for March.",
        demonstrates="Sensitive data protection, identifier exposure block",
        expected="REFUSES - suggests compliant alternative",
        should_refuse=True
    ),
    DemoScenario(
        id=11,
        part=5,
        name="Safe Aggregation",
        question="Which deposit product has the highest average balance?",
        demonstrates="Privacy-safe aggregation, product-level grouping",
        expected="AVG(balance_after) by product_type with k-anonymity"
    ),
    
    # Part 6: Cost & Query Safety
    DemoScenario(
        id=12,
        part=6,
        name="Large Result Request",
        question="Show all events in the dataset.",
        demonstrates="Query safety limits, full extraction prevention",
        expected="Summary or limited results, explains restriction"
    ),
    
    # Part 7: End-to-End Demo
    DemoScenario(
        id=13,
        part=7,
        name="Full Pipeline Demo",
        question="Show the monthly net flow trend for chequing accounts and explain the key drivers.",
        demonstrates="Full orchestrator, multi-agent collaboration, SQL + Explanation",
        expected="Trend data + interpretation + stated assumptions"
    ),
]

PART_NAMES = {
    1: "Core Analytics (SQL + RAG Schema)",
    2: "Intent Routing & RAG Knowledge",
    3: "Analytical Explanation",
    4: "Default Assumptions",
    5: "Governance & Privacy",
    6: "Cost & Query Safety",
    7: "End-to-End Pipeline (LangChain + RAG)"
}


def print_header():
    """Print demo header."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           Agentic Analytics Orchestrator - Demo Suite            ║
║             Enterprise Banking Analytics Demos                   ║
╚══════════════════════════════════════════════════════════════════╝
""")


def print_part_header(part: int):
    """Print part header."""
    name = PART_NAMES.get(part, f"Part {part}")
    print(f"""
┌──────────────────────────────────────────────────────────────────┐
│  PART {part}: {name:<54} │
└──────────────────────────────────────────────────────────────────┘
""")


def print_demo_box(demo: DemoScenario, status: str = "running"):
    """Print demo information box."""
    refuse_tag = " [SHOULD REFUSE]" if demo.should_refuse else ""
    
    # Truncate long questions for display
    q_display = demo.question[:52] + "..." if len(demo.question) > 55 else demo.question
    d_display = demo.demonstrates[:48] + "..." if len(demo.demonstrates) > 50 else demo.demonstrates
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  DEMO {demo.id}: {demo.name:<43}{refuse_tag:>10} ║
╠══════════════════════════════════════════════════════════════════╣
║  Q: {q_display:<60} ║
║  Tests: {d_display:<56} ║
╚══════════════════════════════════════════════════════════════════╝
""")


def check_demo_result(demo: DemoScenario, result: dict) -> tuple[bool, str]:
    """
    Check if demo result matches expectations.
    
    Returns (passed, reason)
    """
    # Check for errors
    if result.get("error"):
        return False, f"Error: {result['error']}"
    
    # Check scope rejection
    is_rejected = not result.get("is_in_scope", True)
    
    if demo.should_refuse:
        # Demo expected refusal
        if is_rejected:
            return True, "Correctly refused (privacy/safety)"
        else:
            # Check if response indicates refusal even if scope passed
            response = result.get("final_response", "").lower()
            refusal_indicators = ["cannot", "not allowed", "privacy", "refuse", "sorry"]
            if any(ind in response for ind in refusal_indicators):
                return True, "Query modified/refused for safety"
            return False, "Should have refused but executed"
    else:
        # Demo expected execution
        if is_rejected:
            return False, "Incorrectly refused valid query"
        
        # Check confidence
        confidence = result.get("confidence", "low")
        if confidence in ("high", "medium"):
            return True, f"Executed successfully ({confidence} confidence)"
        else:
            return False, f"Low confidence: {confidence}"


def run_demo(demo: DemoScenario, verbose: bool = False) -> dict:
    """Run a single demo scenario."""
    print_demo_box(demo)
    
    if not demo.is_query:
        # Command-based demo
        print(f"  📋 Command: python main.py {demo.question}")
        print(f"  ℹ️  Run this command manually to see results")
        print(f"  Expected: {demo.expected}")
        return {"skipped": True, "reason": "command-based demo"}
    
    print("  ⏳ Processing...")
    print()
    
    start_time = time.time()
    
    try:
        result = run_query(demo.question, enable_logging=True)
        elapsed = time.time() - start_time
        
        # Print response
        response = result.get("final_response", "No response")
        print("  " + "─" * 60)
        
        # Truncate long responses
        lines = response.split("\n")
        for i, line in enumerate(lines[:15]):  # Max 15 lines
            print(f"  {line}")
        if len(lines) > 15:
            print(f"  ... ({len(lines) - 15} more lines)")
        
        print("  " + "─" * 60)
        
        # Check result
        passed, reason = check_demo_result(demo, result)
        
        # Print stats
        self_scores = result.get("self_scores", {})
        overall = self_scores.get("overall", 0)
        confidence = result.get("confidence", "unknown")
        tokens = result.get("total_tokens", 0)
        
        print()
        status_icon = "✓" if passed else "✗"
        print(f"  {status_icon} {reason}")
        print(f"  ✓ Completed in {elapsed:.2f}s")
        print(f"  ✓ Confidence: {score_to_stars(overall)} ({overall:.0f}/100 - {confidence})")
        print(f"  ✓ Tokens: {tokens}")
        
        if verbose and self_scores:
            print(f"\n  Score breakdown:")
            for key, value in self_scores.items():
                if key not in ("overall", "confidence", "issues"):
                    print(f"    • {key}: {value}")
        
        result["_passed"] = passed
        result["_reason"] = reason
        return result
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"error": str(e), "_passed": False, "_reason": str(e)}


def run_demos(
    demos: List[DemoScenario],
    interactive: bool = False,
    verbose: bool = False
):
    """Run multiple demos."""
    print_header()
    
    total = len(demos)
    passed = 0
    failed = 0
    skipped = 0
    
    current_part = None
    results = []
    
    for i, demo in enumerate(demos):
        # Print part header if changed
        if demo.part != current_part:
            current_part = demo.part
            print_part_header(current_part)
        
        result = run_demo(demo, verbose=verbose)
        results.append((demo, result))
        
        if result.get("skipped"):
            skipped += 1
        elif result.get("_passed", False):
            passed += 1
        else:
            failed += 1
        
        # Interactive pause
        if interactive and i < total - 1:
            print()
            try:
                input("  Press Enter for next demo (or Ctrl+C to quit)...")
            except KeyboardInterrupt:
                print("\n\n  Demo stopped by user.")
                break
        
        print()
    
    # Summary
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                        DEMO SUMMARY                              ║
╠══════════════════════════════════════════════════════════════════╣""")
    print(f"║  Total: {total:<5}  Passed: {passed:<5}  Failed: {failed:<5}  Skipped: {skipped:<5}    ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    
    # Show failed demos
    if failed > 0:
        print("\n  ⚠️  Failed demos:")
        for demo, result in results:
            if not result.get("skipped") and not result.get("_passed", False):
                print(f"     • Demo {demo.id}: {demo.name} - {result.get('_reason', 'unknown')}")
    
    if failed == 0 and skipped < total:
        print("\n  ✅ All demos completed successfully!")
    
    return passed, failed, skipped


def list_demos():
    """List all available demos."""
    print("\nAvailable Demos:\n")
    
    current_part = None
    for demo in DEMOS:
        if demo.part != current_part:
            current_part = demo.part
            print(f"\n  Part {current_part}: {PART_NAMES[current_part]}")
            print("  " + "─" * 50)
        
        refuse_tag = " [REFUSE]" if demo.should_refuse else ""
        query_type = "query" if demo.is_query else "command"
        print(f"    {demo.id:2}. {demo.name:<35} [{query_type}]{refuse_tag}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Run demo scenarios for the Agentic Analytics Orchestrator"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Pause between demos"
    )
    parser.add_argument(
        "--part", "-p",
        type=int,
        choices=[1, 2, 3, 4, 5, 6, 7],
        help="Run demos from specific part only"
    )
    parser.add_argument(
        "--demo", "-d",
        type=int,
        help="Run single demo by ID"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all demos"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick demo (1, 9, 13 only)"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_demos()
        return
    
    # Filter demos
    demos = DEMOS
    
    if args.quick:
        demos = [d for d in DEMOS if d.id in (1, 9, 13)]
    elif args.demo:
        demos = [d for d in DEMOS if d.id == args.demo]
        if not demos:
            print(f"Demo {args.demo} not found. Use --list to see available demos.")
            sys.exit(1)
    elif args.part:
        demos = [d for d in DEMOS if d.part == args.part]
    
    # Validate settings for query-based demos
    has_queries = any(d.is_query for d in demos)
    if has_queries:
        valid, msg = settings.validate()
        if not valid:
            print(f"❌ Configuration error: {msg}")
            sys.exit(1)
    
    passed, failed, skipped = run_demos(demos, interactive=args.interactive, verbose=args.verbose)
    
    # Exit code based on results
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
