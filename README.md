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
  Generates and executes analytical queries within approved constraints. In Phase 2 (separate repo), this becomes an orchestrated SQL engine: its own orchestrator plans then executes by calling domain specialist sub-agents (e.g. Digital Marketing, Transaction, Customer, Campaign) as tools and passing results between them.

- **Data Quality Agent**  
  Performs basic validation and anomaly checks on results.

- **Explanation Agent**  
  Translates analytical outputs into business-readable insights.

- **RAG Tool (Optional)**  
  Provides lightweight knowledge grounding when additional context is required.

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

## Documentation

| Document | Description |
|----------|-------------|
| [STRUCTURE.md](./STRUCTURE.md) | Folder and file organization |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System architecture and flowcharts |
| [docs/ROADMAP.md](./docs/ROADMAP.md) | Phased development plan (Phase 1–4) |

---

## Tech Stack

**Phase 1 (this repo):**
| Layer | Tool |
|-------|------|
| Orchestration | **LangGraph** (LangChain) |
| LLM | OpenAI / Anthropic / Gemini (pluggable) |
| SQL Engine | **DuckDB** (local, reads CSV) |
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

<!-- Fill in manually: current phase, progress, or next steps -->

---

## License

MIT License