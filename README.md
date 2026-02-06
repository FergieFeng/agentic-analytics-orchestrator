# Agentic Analytics Orchestrator

A governed, multi-agent analytics system that demonstrates how an orchestrator coordinates specialized agents (definition, SQL, data quality, explanation, and retrieval) to handle ambiguous analytical questions with accuracy, traceability, and risk control.

---

## Motivation

Many analytical questions are not purely computational — they require
interpretation, validation, and explanation before and after execution.
Single-agent systems often collapse these steps into one prompt, making
behavior hard to control and outcomes difficult to trust.

This project explores an alternative approach:
**treat analytics as a coordinated, multi-agent decision process**.

---

## What This Project Demonstrates

- How an Orchestrator can act as a central decision-maker rather than a router
- How specialized agents collaborate under uncertainty
- How governance and guardrails reduce analytical and hallucination risk
- How analytical results can be made traceable and explainable

This is a **system design project**, not a chatbot or a SQL generator.

---

## Core Architecture

### Orchestrator
The Orchestrator is responsible for:
- Interpreting user intent
- Deciding which agents to invoke and in what order
- Enforcing scope and safety constraints
- Coordinating outputs into a coherent analytical response

### Specialist Agents
Each agent has a clearly bounded responsibility:

- **Definition Agent**  
  Interprets metrics, dimensions, and analytical intent.

- **SQL Agent**  
  Generates and executes analytical queries within approved constraints. In Phase 2 (separate repo), this becomes an orchestrated SQL engine: its own orchestrator plans then executes by calling domain specialist sub-agents as tools and passing results between them.

- **Data Quality Agent**  
  Performs basic validation and anomaly checks on results.

- **Explanation Agent**  
  Translates analytical outputs into business-readable insights.

- **RAG Module**  
  Provides retrieval-augmented generation using ChromaDB vector store.
  - Indexes business glossary, metrics, and schema definitions
  - Retrieves relevant context for each agent
  - Enables history-based similarity search for past queries

Agents do not call each other directly — all coordination flows through the Orchestrator.

**Flow (Phase 1, this repo):** See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for the Phase 1 flowchart (orchestrator + simple agents, no nesting).

---

## Project Scope

**In scope**
- Multi-agent orchestration
- Analytical ambiguity handling
- Guardrails and evaluation hooks
- Single-table analytical workflows

**Out of scope** (handled in other repos per roadmap)
- Deep machine learning models
- Production-grade infrastructure
- Multi-agent SQL engine (orchestrator + domain specialists, plan-then-execute) → Phase 2 repo
- Deep RAG pipelines → Phase 3 repo

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run a query
python main.py "What is the total deposit amount by channel?"

# Interactive mode
python main.py -i

# Launch web UI
streamlit run src/apps/streamlit_app.py
```

---

## Demo

The project includes 13 demo scenarios showcasing all capabilities:

```bash
# Terminal: Run all demos
python src/apps/run_demo.py

# Terminal: Interactive mode (pause between demos)
python src/apps/run_demo.py --interactive

# Web UI: Launch Streamlit app
streamlit run src/apps/streamlit_app.py
```

| Part | Focus | Demos |
|------|-------|-------|
| 1-3 | Core Analytics | SQL + RAG schema context, explanations |
| 4-5 | RAG Knowledge | Definition queries using ChromaDB retrieval |
| 6-10 | Safety | K-anonymity, scope guard, privacy refusals |
| 11-13 | End-to-End | Full LangChain + RAG pipeline |

See [docs/DEMO.md](./docs/DEMO.md) for the complete demo guide.

---

## Documentation

| Document | Description |
|----------|-------------|
| [STRUCTURE.md](./STRUCTURE.md) | Folder and file organization |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System architecture and design |
| [docs/DEMO.md](./docs/DEMO.md) | Demo guide with 12 scenarios |
| [docs/DIAGRAMS.md](./docs/DIAGRAMS.md) | Visual workflow diagrams |
| [docs/ROADMAP.md](./docs/ROADMAP.md) | Phased development plan (Phase 1–4) |

---

## Tech Stack

**Phase 1 (this repo):**
| Layer | Tool |
|-------|------|
| Orchestration | **LangGraph** (LangChain) |
| LLM | **LangChain + OpenAI** (gpt-4o-mini) |
| Embeddings | **OpenAI** (text-embedding-3-small) |
| Vector DB | **ChromaDB** (persistent local storage) |
| SQL Engine | **DuckDB** (local, reads CSV) |
| Query History | **SQLite** (query_logs.db) |
| Language | Python 3.11+ |
| Testing | pytest |
| CI/CD | GitHub Actions |

**Phase 2+ (future repos):**
| Layer | Tool |
|-------|------|
| SQL Engine | **BigQuery** |
| LLM | **Vertex AI** (Gemini) |
| Agent Framework | **Google ADK** |
| Cloud | **GCP** |

---

## Evaluation

Key metrics to measure agent system performance:

- **Routing accuracy** — did the orchestrator call the right agents?
- **SQL validity** — did the SQL agent produce executable, correct queries?
- **Output completeness** — did the response answer the user's question?
- **Latency** — end-to-end response time
- **Guardrail triggers** — how often did safety checks intervene?

Logging all agent decisions for traceability and compliance.

---

## Design Philosophy

- Orchestration over prompt complexity
- Clear agent boundaries over monolithic logic
- Explainability and traceability over raw performance
- Extensibility without rewriting core control flow

---

## Status

**Phase 1: Complete** ✅

- ✅ Multi-agent orchestration (LangGraph)
- ✅ LangChain LLM abstraction (`ChatOpenAI`)
- ✅ RAG integration (ChromaDB + OpenAI embeddings)
- ✅ Vector similarity search for past queries
- ✅ 13 enterprise demo scenarios
- ✅ Self-evaluation and user feedback system
- ✅ Streamlit UI + terminal demo runner

---

## License

MIT License