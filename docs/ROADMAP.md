# Roadmap – Agentic Analytics (Multi-Repo Plan)

Overall idea: one vision for governed, multi-agent analytics — then **split into separate repos** to go deep one by one. Each phase is its own repository. See [ARCHITECTURE.md](./ARCHITECTURE.md) for the flowchart.

---

## Phase 1 · This Repo

**Repository:** `agentic-analytics-orchestrator` (this repo)

**Focus:** Orchestrator + multi-agent collaboration.

Design a governed multi-agent system where an orchestrator coordinates specialist agents to handle ambiguous analytics problems.

**Stack:** Python, LangGraph, DuckDB (local CSV), OpenAI/Anthropic (pluggable LLM).

---

## Phase 2 · Separate Repo

**Repository:** `agentic-sql-engine`

**Focus:** SQL as a multi-agent system (orchestrated SQL engine).

The "SQL Agent" from Phase 1 is deepened into its own **orchestrator + specialist agents**:

- **Domain knowledge split by specialist:** e.g. Digital Marketing Agent, Transaction Agent, Customer Agent, Campaign Agent — each owns one domain slice.
- **SQL orchestrator (LLM):** Decides which specialist(s) to call and in what order. Generates a **plan first**, then **executes** it.
- **Specialists as tools:** Each domain specialist is invoked as a tool, returns structured details to the orchestrator; the orchestrator passes results to the next agent as needed. No direct agent-to-agent calls — all flow through the SQL orchestrator.

So: same orchestration pattern as Phase 1, applied inside the SQL boundary. Analytical SQL is covered by domain-focused specialists (Digital Marketing, Transaction, Customer, Campaign) rather than one monolithic agent.

**Stack:** Python, Google ADK, BigQuery, Vertex AI (Gemini).

---

## Phase 3 · Separate Repo

**Repository:** `agentic-rag-analytics`

**Focus:** RAG for analytics grounding.

Use embeddings and retrieval to ground analytics in schema, metrics, and business knowledge.

**Stack:** Python, Vertex AI Embeddings, Vector DB (Pinecone / Weaviate / AlloyDB), BigQuery.

---

## Phase 4 · Optional (Future)

**Repository:** `agentic-analytics-workflows`

**Focus:** Agent-driven workflows.

Extend agents from "answering questions" to executing repeatable business workflows.

*Fully future; not part of current planning.*

---

## Summary

| Phase | Repo | Focus |
|-------|------|--------|
| 1 | agentic-analytics-orchestrator | Orchestrator + multi-agent collaboration |
| 2 | agentic-sql-engine | Multi-agent SQL engine (orchestrator + specialists, plan-then-execute) |
| 3 | agentic-rag-analytics | RAG for analytics grounding |
| 4 (optional) | agentic-analytics-workflows | Agent-driven workflows |

Phases 1–3 are the active sequence to finish; Phase 4 is optional and later.

---

## Guiding Principle

This plan prioritizes **orchestration, decision flow, and agent collaboration** first, then going deep on SQL and RAG in dedicated repos, over optimizing any single piece too early.
