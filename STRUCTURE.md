# Project Structure

This document describes the folder and file organization for the Agentic Analytics Orchestrator.

---

## Overview

```
agentic-analytics-orchestrator/
│
├── .github/workflows/          # CI/CD pipelines
├── apps/                       # Automation & utility scripts
├── data/                       # Sample data, schema, knowledge
├── docs/                       # Documentation (architecture, roadmap)
├── src/                        # Source code
│   ├── orchestrator/           # Main orchestrator (LangGraph)
│   ├── specialists/            # Specialist agents
│   ├── tools/                  # Shared tools
│   ├── guardrails/             # Safety checks
│   ├── evaluation/             # Logging, metrics, tracing
│   └── config/                 # Configuration
├── tests/                      # Test files
├── README.md                   # Project overview
├── STRUCTURE.md                # This file
├── requirements.txt            # Dependencies
└── main.py                     # Entry point
```

---

## Detailed Structure

```
agentic-analytics-orchestrator/
│
├── .github/
│   └── workflows/
│       └── test.yml                     # CI: lint + pytest on push/PR
│
├── apps/                                # Automation scripts
│   ├── scaffold_agent.py                # Generate new specialist folder
│   ├── generate_schema_doc.py           # CSV → schema.md
│   ├── run_eval.py                      # Run evaluation suite
│   ├── generate_test_cases.py           # Sample questions → pytest cases
│   └── export_trace_report.py           # Agent traces → Markdown report
│
├── data/
│   ├── sample_events.csv                # Sample banking events
│   ├── schema.json                      # Column definitions & enum values
│   └── knowledge.json                   # Business glossary & metric definitions
│
├── docs/
│   ├── ARCHITECTURE.md                  # System architecture and flowcharts
│   └── ROADMAP.md                       # Phased development plan
│
├── src/
│   ├── __init__.py
│   │
│   ├── orchestrator/                    # Main orchestrator (LangGraph)
│   │   ├── __init__.py
│   │   ├── graph.py                     # LangGraph state machine
│   │   ├── state.py                     # Shared state schema
│   │   ├── router.py                    # Routing logic
│   │   └── prompt.md                    # Orchestrator system prompt
│   │
│   ├── specialists/                     # Specialist agents
│   │   ├── __init__.py
│   │   │
│   │   ├── definition_agent/            # Metric & intent interpretation
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   └── prompt.md
│   │   │
│   │   ├── sql_agent/                   # SQL generation & execution
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   └── prompt.md
│   │   │
│   │   ├── data_quality_agent/          # Result validation & anomaly checks
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   └── prompt.md
│   │   │
│   │   ├── explanation_agent/           # Business insight generation
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   └── prompt.md
│   │   │
│   │   └── rag_tool/                    # Lightweight retrieval (optional)
│   │       ├── __init__.py
│   │       ├── retriever.py
│   │       └── index_builder.py
│   │
│   ├── tools/                           # Shared tools
│   │   ├── __init__.py
│   │   ├── duckdb_tool.py               # SQL execution via DuckDB
│   │   └── schema_tool.py               # Table schema lookup
│   │
│   ├── guardrails/                      # Safety checks
│   │   ├── __init__.py
│   │   ├── scope_guard.py               # Reject off-topic questions
│   │   ├── sql_guard.py                 # Validate SQL before execution
│   │   └── output_guard.py              # Check output before returning
│   │
│   ├── evaluation/                      # Metrics and observability
│   │   ├── __init__.py
│   │   ├── logger.py                    # Structured JSON logging
│   │   ├── metrics.py                   # Routing accuracy, SQL validity
│   │   └── tracer.py                    # Agent call tracing
│   │
│   └── config/                          # Configuration
│       ├── __init__.py
│       ├── settings.py                  # Environment and model config
│       └── schema.json                  # Table schema definition
│
├── tests/
│   ├── __init__.py
│   ├── test_orchestrator.py
│   ├── test_sql_agent.py
│   ├── test_duckdb_tool.py
│   └── test_guardrails.py
│
├── .env.example                         # Example environment variables
├── .gitignore
├── LICENSE
├── README.md                            # Project overview
├── STRUCTURE.md                         # This file
├── requirements.txt                     # Python dependencies
└── main.py                              # Entry point
```

---

## Folder Reference

| Folder | Purpose |
|--------|---------|
| `apps/` | Automation: scaffold agents, generate docs, run evaluations |
| `data/` | Sample data, schema docs, domain knowledge |
| `docs/` | Architecture diagrams, roadmap, schema documentation |
| `src/orchestrator/` | LangGraph state machine, routing logic |
| `src/specialists/` | Specialist agents (each has `agent.py` + `prompt.md`) |
| `src/tools/` | Shared tools (DuckDB execution, schema lookup) |
| `src/guardrails/` | Safety checks (scope, SQL validation, output) |
| `src/evaluation/` | Logging, metrics, tracing for observability |
| `src/config/` | Settings, environment variables, schema definition |
| `tests/` | pytest test files |

---

## Naming Convention

| Term | Meaning |
|------|---------|
| **Orchestrator** | Main coordinator that routes to specialists |
| **Specialist** | Agent with bounded responsibility (definition, sql, etc.) |
| **Tool** | Utility function a specialist can call (duckdb, schema) |
| **Guardrail** | Safety check before/after agent execution |
