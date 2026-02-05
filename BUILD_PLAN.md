# Build Plan: Phase 1

## Status: ✅ COMPLETE

All core components implemented and tested.

## Build Order (dependencies first)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BUILD ORDER                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Step 1: Foundation                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   config/   │  │   tools/    │  │ guardrails/ │                 │
│  │  settings   │  │  duckdb     │  │ scope_guard │                 │
│  │             │  │  schema     │  │  sql_guard  │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
│         │                │                │                         │
│         └────────────────┼────────────────┘                         │
│                          ▼                                          │
│  Step 2: Specialist Agents                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │  Definition  │ │     SQL      │ │ Data Quality │ │ Explanation│ │
│  │    Agent     │ │    Agent     │ │    Agent     │ │   Agent    │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │
│         │                │                │               │         │
│         └────────────────┼────────────────┼───────────────┘         │
│                          ▼                                          │
│  Step 3: Orchestrator                                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    LangGraph State Machine                   │   │
│  │  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐      │   │
│  │  │ Router │ →  │ Agents │ →  │ Merge  │ →  │ Output │      │   │
│  │  └────────┘    └────────┘    └────────┘    └────────┘      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                          │                                          │
│                          ▼                                          │
│  Step 4: Entry Point                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                       main.py                                │   │
│  │              CLI + Interactive Demo                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Foundation (no LLM calls)

| File | Purpose |
|------|---------|
| `src/config/settings.py` | Load `.env`, expose `OPENAI_API_KEY`, `MODEL_NAME`, etc. |
| `src/tools/duckdb_tool.py` | Execute SQL on CSV via DuckDB, return results |
| `src/tools/schema_tool.py` | Load `schema.json` and `knowledge.json` |
| `src/guardrails/scope_guard.py` | Reject off-topic questions (e.g., "What's the weather?") |
| `src/guardrails/sql_guard.py` | Block dangerous SQL (DROP, DELETE, etc.) |

---

## Step 2: Specialist Agents (LLM-powered)

| Agent | Input | Output | Tools Used |
|-------|-------|--------|------------|
| **Definition Agent** | User question | Clarified intent + metric definitions | `schema_tool` |
| **SQL Agent** | Clarified intent | SQL query + execution results | `duckdb_tool`, `schema_tool` |
| **Data Quality Agent** | Query results | Validation (nulls, outliers, row count) | — |
| **Explanation Agent** | Query results + context | Business insight summary | — |

---

## Step 3: Orchestrator (LangGraph)

The orchestrator is a **state machine** that:

```
User Question
     │
     ▼
┌─────────────┐
│ Scope Guard │ ──(off-topic)──→ Reject
└─────────────┘
     │ (valid)
     ▼
┌─────────────┐
│   Router    │  Decide which agents to invoke
└─────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│   Parallel Agent Execution          │
│  ┌────────┐ ┌─────┐ ┌─────────────┐│
│  │Def.Agt │ │SQL  │ │Data Quality ││
│  └────────┘ └─────┘ └─────────────┘│
└─────────────────────────────────────┘
     │
     ▼
┌─────────────┐
│ Explanation │  Synthesize final answer
└─────────────┘
     │
     ▼
  Response
```

**LangGraph concepts:**
- **State**: Shared dict passed between nodes (question, sql, results, answer)
- **Nodes**: Functions that transform state (each agent is a node)
- **Edges**: Define flow (sequential or conditional branching)

---

## Step 4: Entry Point

`main.py` will:
1. Accept a question (CLI arg or interactive prompt)
2. Run the orchestrator graph
3. Print the final answer with tracing info

---

## What You'll See Working

After building, you can run:
```bash
python main.py "What was the total deposits last month?"
```

And get:
```
[Router] → Definition Agent, SQL Agent
[Definition Agent] Interpreting: total deposits = SUM(event_amount) WHERE event_amount > 0
[SQL Agent] Generated: SELECT SUM(event_amount) FROM sample_events WHERE ...
[SQL Agent] Result: 45,230.00
[Data Quality] ✓ Valid (1 row, no nulls)
[Explanation] Total deposits for January 2024 were $45,230.00 across 15 transactions.

Answer: Total deposits for January 2024 were $45,230.00 across 15 transactions.
```
