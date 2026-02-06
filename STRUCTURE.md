# Project Structure

This document describes the folder and file organization for the Agentic Analytics Orchestrator.

---

## Overview

```
agentic-analytics-orchestrator/
│
├── .github/workflows/          # CI/CD pipelines
├── data/                       # Sample data, schema, knowledge
├── docs/                       # Documentation (architecture, roadmap)
├── prompts/                    # Centralized prompt management
│   ├── system.md               # Global system prompt (privacy, defaults)
│   ├── schema_context.md       # Schema + query constraints
│   ├── guardrails/             # Guardrail prompts
│   └── agents/                 # Agent-specific prompts
├── src/                        # Source code
│   ├── apps/                   # Demo & automation scripts
│   ├── orchestrator/           # Main orchestrator (LangGraph)
│   ├── specialists/            # Specialist agents
│   ├── rag/                    # RAG: Vector store, embeddings, retrieval
│   ├── tools/                  # Shared tools
│   ├── guardrails/             # Safety checks
│   ├── evaluation/             # Logging, metrics, tracing
│   └── config/                 # Configuration + prompt loader
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
├── data/
│   ├── sample_events.csv                # Sample banking events (Jan-Mar 2024)
│   ├── schema.json                      # Column definitions & enum values
│   ├── knowledge.json                   # Business glossary & metric definitions
│   ├── chroma_db/                       # ChromaDB vector store (auto-generated)
│   └── query_logs.db                    # SQLite query history (auto-generated)
│
├── prompts/                             # Centralized prompt management
│   ├── system.md                        # Global rules (privacy, defaults, style)
│   ├── schema_context.md                # Schema + query-building constraints
│   ├── guardrails/
│   │   ├── scope.md                     # In/out of scope definitions
│   │   └── sql_safety.md                # SQL validation + privacy rules
│   └── agents/
│       ├── definition.md                # Definition agent prompt
│       ├── sql.md                       # SQL agent prompt
│       ├── quality.md                   # Data quality agent prompt
│       └── explanation.md               # Explanation agent prompt
│
├── docs/
│   ├── ARCHITECTURE.md                  # System architecture and design
│   ├── DEMO.md                          # Demo guide with 12 scenarios
│   ├── DIAGRAMS.md                      # Visual workflow diagrams
│   └── ROADMAP.md                       # Phased development plan
│
├── src/
│   ├── __init__.py
│   │
│   ├── apps/                            # Demo & automation scripts
│   │   ├── __init__.py
│   │   ├── run_demo.py                  # Terminal demo runner (13 scenarios)
│   │   ├── streamlit_app.py             # Web UI for interactive demos
│   │   ├── scaffold_agent.py            # Generate new specialist folder
│   │   ├── generate_schema_doc.py       # CSV → schema.md
│   │   ├── run_eval.py                  # Run evaluation suite
│   │   ├── generate_test_cases.py       # Sample questions → pytest cases
│   │   └── export_trace_report.py       # Agent traces → Markdown report
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
│   │   └── rag_tool/                    # (Deprecated: moved to src/rag/)
│   │       └── ...
│   │
│   ├── rag/                             # RAG: Retrieval-Augmented Generation
│   │   ├── __init__.py                  # Module exports
│   │   ├── embedder.py                  # OpenAI text-embedding-3-small
│   │   ├── vector_store.py              # ChromaDB vector storage
│   │   ├── indexer.py                   # Index knowledge.json & schema.json
│   │   └── retriever.py                 # Query vectors for context
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
│   ├── evaluation/                      # Logging, scoring, and feedback
│   │   ├── __init__.py
│   │   ├── logger.py                    # Session-based structured logging
│   │   ├── query_store.py               # SQLite database for query history
│   │   ├── self_eval.py                 # Automatic quality scoring
│   │   ├── feedback.py                  # User feedback collection
│   │   ├── history_search.py            # Vector similarity search for past queries
│   │   ├── metrics.py                   # Performance metrics
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
| `data/` | Sample data, schema JSON, domain knowledge JSON, vector DB |
| `docs/` | Architecture, visual diagrams, roadmap |
| `prompts/` | Centralized prompt files (system, guardrails, agents) |
| `src/apps/` | Demo scripts, automation, evaluation runners |
| `src/orchestrator/` | LangGraph state machine, routing logic |
| `src/specialists/` | Specialist agent implementations |
| `src/rag/` | RAG: embeddings, ChromaDB vector store, retrieval |
| `src/tools/` | Shared tools (DuckDB execution, schema lookup) |
| `src/guardrails/` | Safety checks (scope, SQL validation) |
| `src/evaluation/` | Session logging, self-evaluation, user feedback, history search |
| `src/config/` | Settings, LLM client, prompt loader |
| `tests/` | pytest test files |

---

## Naming Convention

| Term | Meaning |
|------|---------|
| **Orchestrator** | Main coordinator that routes to specialists |
| **Specialist** | Agent with bounded responsibility (definition, sql, etc.) |
| **Tool** | Utility function a specialist can call (duckdb, schema) |
| **Guardrail** | Safety check before/after agent execution |
