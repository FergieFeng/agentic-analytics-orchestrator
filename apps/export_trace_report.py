#!/usr/bin/env python3
"""
Export Trace Report: Convert agent traces to Markdown report.

Usage:
    python apps/export_trace_report.py --input traces.json --output report.md
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict


def format_trace(trace: Dict, indent: int = 0) -> str:
    """Format a single trace span as Markdown."""
    
    prefix = "  " * indent
    md = f"{prefix}- **{trace['name']}**"
    
    if trace.get('duration_ms'):
        md += f" ({trace['duration_ms']:.1f}ms)"
    
    md += "\n"
    
    if trace.get('input'):
        md += f"{prefix}  - Input: `{str(trace['input'])[:100]}`\n"
    
    if trace.get('output'):
        md += f"{prefix}  - Output: `{str(trace['output'])[:100]}`\n"
    
    if trace.get('error'):
        md += f"{prefix}  - **Error**: {trace['error']}\n"
    
    # Recurse into children
    for child in trace.get('children', []):
        md += format_trace(child, indent + 1)
    
    return md


def generate_report(traces: List[Dict]) -> str:
    """Generate Markdown report from traces."""
    
    md = "# Agent Trace Report\n\n"
    md += f"Generated: {datetime.now().isoformat()}\n\n"
    md += f"Total traces: {len(traces)}\n\n"
    
    md += "---\n\n"
    
    for i, trace in enumerate(traces, 1):
        md += f"## Trace {i}: {trace.get('name', 'Unknown')}\n\n"
        
        if trace.get('start_time'):
            md += f"- Start: {trace['start_time']}\n"
        if trace.get('end_time'):
            md += f"- End: {trace['end_time']}\n"
        if trace.get('duration_ms'):
            md += f"- Duration: {trace['duration_ms']:.1f}ms\n"
        
        md += "\n### Execution Flow\n\n"
        md += format_trace(trace)
        md += "\n---\n\n"
    
    # Summary
    md += "## Summary\n\n"
    
    total_duration = sum(t.get('duration_ms', 0) for t in traces)
    avg_duration = total_duration / len(traces) if traces else 0
    errors = sum(1 for t in traces if t.get('error'))
    
    md += f"- Total traces: {len(traces)}\n"
    md += f"- Total duration: {total_duration:.1f}ms\n"
    md += f"- Average duration: {avg_duration:.1f}ms\n"
    md += f"- Errors: {errors}\n"
    
    return md


def main():
    parser = argparse.ArgumentParser(description="Export trace report")
    parser.add_argument("--input", help="Input JSON file with traces")
    parser.add_argument("--output", default="docs/trace_report.md", help="Output Markdown file")
    
    args = parser.parse_args()
    
    # Load traces or use sample
    if args.input and Path(args.input).exists():
        with open(args.input) as f:
            traces = json.load(f)
    else:
        # Sample trace for demo
        traces = [
            {
                "name": "sample_request",
                "start_time": "2024-01-15T10:00:00",
                "end_time": "2024-01-15T10:00:01",
                "duration_ms": 1000,
                "children": [
                    {"name": "definition_agent", "duration_ms": 200, "output": {"metric": "sum"}},
                    {"name": "sql_agent", "duration_ms": 500, "output": {"sql": "SELECT..."}},
                    {"name": "explanation_agent", "duration_ms": 300, "output": {"text": "..."}}
                ]
            }
        ]
    
    # Generate report
    report = generate_report(traces)
    
    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)
    
    print(f"Generated report: {output_path}")


if __name__ == "__main__":
    main()
