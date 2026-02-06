#!/usr/bin/env python3
"""
Generate Schema Doc: Create schema.md from CSV or schema.json.

Usage:
    python src/apps/generate_schema_doc.py
    python src/apps/generate_schema_doc.py --source data/sample_events.csv
    python src/apps/generate_schema_doc.py --from-json src/config/schema.json
"""

import argparse
import json
from pathlib import Path

import duckdb


def generate_from_csv(csv_path: str) -> str:
    """Generate schema documentation from a CSV file."""
    
    # Get schema from DuckDB
    result = duckdb.sql(f"DESCRIBE SELECT * FROM '{csv_path}'").fetchall()
    
    # Get sample values
    samples = duckdb.sql(f"SELECT * FROM '{csv_path}' LIMIT 3").fetchall()
    columns = [desc[0] for desc in duckdb.sql(f"DESCRIBE SELECT * FROM '{csv_path}'").description]
    
    # Build markdown
    md = f"# Schema: {Path(csv_path).stem}\n\n"
    md += f"Source: `{csv_path}`\n\n"
    md += "## Columns\n\n"
    md += "| Column | Type | Description |\n"
    md += "|--------|------|-------------|\n"
    
    for col in result:
        col_name = col[0]
        col_type = col[1]
        md += f"| {col_name} | {col_type} | TODO: Add description |\n"
    
    md += "\n## Sample Data\n\n"
    md += "| " + " | ".join(columns) + " |\n"
    md += "| " + " | ".join(["---"] * len(columns)) + " |\n"
    
    for row in samples:
        md += "| " + " | ".join(str(v)[:20] for v in row) + " |\n"
    
    return md


def generate_from_json(json_path: str) -> str:
    """Generate schema documentation from schema.json."""
    
    with open(json_path) as f:
        schema = json.load(f)
    
    md = f"# Schema: {schema.get('table', 'Unknown')}\n\n"
    md += f"{schema.get('description', '')}\n\n"
    md += f"Source: `{schema.get('source', 'N/A')}`\n\n"
    
    md += "## Columns\n\n"
    md += "| Column | Type | Description | Values |\n"
    md += "|--------|------|-------------|--------|\n"
    
    for col in schema.get("columns", []):
        values = ", ".join(col.get("values", [])) if col.get("values") else ""
        md += f"| {col['name']} | {col['type']} | {col.get('description', '')} | {values} |\n"
    
    if schema.get("metrics"):
        md += "\n## Pre-defined Metrics\n\n"
        md += "| Metric | Description | SQL |\n"
        md += "|--------|-------------|-----|\n"
        
        for metric in schema["metrics"]:
            md += f"| {metric['name']} | {metric['description']} | `{metric['sql']}` |\n"
    
    return md


def main():
    parser = argparse.ArgumentParser(description="Generate schema documentation")
    parser.add_argument("--source", default="data/sample_events.csv", help="CSV source file")
    parser.add_argument("--from-json", help="Generate from schema.json instead of CSV")
    parser.add_argument("--output", default="docs/schema.md", help="Output file path")
    
    args = parser.parse_args()
    
    if args.from_json:
        md = generate_from_json(args.from_json)
    else:
        md = generate_from_csv(args.source)
    
    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md)
    
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
