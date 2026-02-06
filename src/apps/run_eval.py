#!/usr/bin/env python3
"""
Run Eval: Execute evaluation suite and output metrics.

Usage:
    python src/apps/run_eval.py
    python src/apps/run_eval.py --questions eval_questions.json
"""

import argparse
import json
import time
from pathlib import Path
from typing import List, Dict

# TODO: Import orchestrator when implemented
# from src.orchestrator import create_graph


def load_test_questions(path: str = None) -> List[Dict]:
    """Load test questions from file or use defaults."""
    
    if path and Path(path).exists():
        with open(path) as f:
            return json.load(f)
    
    # Default test questions
    return [
        {
            "question": "What is the total deposit amount by channel?",
            "expected_agents": ["definition_agent", "sql_agent", "data_quality_agent", "explanation_agent"],
            "expected_contains": ["DIGITAL", "BRANCH"]
        },
        {
            "question": "How many customers made transactions?",
            "expected_agents": ["definition_agent", "sql_agent"],
            "expected_contains": ["customer"]
        },
        {
            "question": "What's the weather today?",
            "expected_agents": [],
            "expected_out_of_scope": True
        }
    ]


def run_evaluation(questions: List[Dict]) -> Dict:
    """Run evaluation on test questions."""
    
    results = {
        "total": len(questions),
        "passed": 0,
        "failed": 0,
        "details": []
    }
    
    for q in questions:
        start_time = time.time()
        
        # TODO: Run through orchestrator
        # response = orchestrator.invoke({"user_question": q["question"]})
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Placeholder evaluation
        detail = {
            "question": q["question"],
            "duration_ms": duration_ms,
            "passed": True,  # TODO: Implement actual checks
            "checks": []
        }
        
        results["details"].append(detail)
        if detail["passed"]:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    return results


def print_report(results: Dict):
    """Print evaluation report."""
    
    print("\n" + "=" * 60)
    print("EVALUATION REPORT")
    print("=" * 60)
    print(f"\nTotal: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Pass Rate: {results['passed'] / results['total'] * 100:.1f}%")
    
    print("\n" + "-" * 60)
    print("DETAILS")
    print("-" * 60)
    
    for detail in results["details"]:
        status = "✓" if detail["passed"] else "✗"
        print(f"\n{status} {detail['question'][:50]}...")
        print(f"  Duration: {detail['duration_ms']:.1f}ms")


def main():
    parser = argparse.ArgumentParser(description="Run evaluation suite")
    parser.add_argument("--questions", help="Path to test questions JSON")
    parser.add_argument("--output", help="Output results to JSON file")
    
    args = parser.parse_args()
    
    questions = load_test_questions(args.questions)
    results = run_evaluation(questions)
    print_report(results)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
