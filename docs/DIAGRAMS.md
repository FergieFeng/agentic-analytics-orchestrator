# System Diagrams

Visual documentation of the Agentic Analytics Orchestrator architecture and workflows.

> **Note:** Keep this file updated as the system evolves.

---

## Table of Contents

1. [Overall Architecture](#overall-architecture)
2. [Build Order](#build-order)
3. [Prompt Composition](#prompt-composition)
4. [Agent Pipeline](#agent-pipeline)
5. [SQL Agent Flow](#sql-agent-flow)
6. [Privacy Filtering](#privacy-filtering)
7. [RAG Pipeline](#rag-pipeline)
8. [Logging & Evaluation](#logging--evaluation)

---

## Overall Architecture

The orchestrator coordinates specialist agents to answer analytics questions.

```
                              User Question
                                    │
                                    ▼
                         ┌──────────────────┐
                         │   Orchestrator   │
                         │ (LangGraph)      │
                         └────────┬─────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
   ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
   │ Definition  │        │    SQL      │        │ Explanation │
   │   Agent     │        │   Agent     │        │   Agent     │
   └─────────────┘        └─────────────┘        └─────────────┘
          │                       │                       │
          │                       ▼                       │
          │               ┌─────────────┐                 │
          │               │   DuckDB    │                 │
          │               │   (Data)    │                 │
          │               └─────────────┘                 │
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Final Response  │
                         │  (with insights) │
                         └──────────────────┘
```

### Phase 2+ Vision: SQL Agent as Sub-Orchestrator

```
                         ┌──────────────────────────┐
                         │      Orchestrator        │
                         │    (Main Coordinator)    │
                         └────────────┬─────────────┘
                                      │
        ┌─────────────┬───────────────┼───────────────┬─────────────┐
        │             │               │               │             │
        ▼             ▼               ▼               ▼             ▼
   ┌─────────┐  ┌─────────┐    ┌───────────┐   ┌─────────┐   ┌─────────┐
   │  Def    │  │  RAG    │    │    SQL    │   │ Quality │   │ Explain │
   │  Agent  │  │  Agent  │    │   Agent   │   │  Agent  │   │  Agent  │
   └─────────┘  └─────────┘    └─────┬─────┘   └─────────┘   └─────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
             ┌───────────┐    ┌───────────┐    ┌───────────┐
             │  Digital  │    │Transaction│    │  Customer │
             │ Marketing │    │  Domain   │    │  Domain   │
             │  Domain   │    │ Specialist│    │ Specialist│
             └───────────┘    └───────────┘    └───────────┘
```

---

## Build Order

Dependencies flow from foundation to entry point.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BUILD ORDER                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Step 1: Foundation                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   config/   │  │   tools/    │  │ guardrails/ │                 │
│  │  settings   │  │  duckdb     │  │ scope_guard │                 │
│  │  prompts    │  │  schema     │  │  sql_guard  │                 │
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

## Prompt Composition

Prompts are composed hierarchically for each agent.

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROMPT COMPOSITION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                                                │
│  │  system.md  │  ← Global rules (privacy, defaults, style)     │
│  └──────┬──────┘                                                │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────┐                                            │
│  │ schema_context  │  ← Schema + privacy constraints            │
│  │ (from .json)    │                                            │
│  └────────┬────────┘                                            │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────────────────────────────┐                    │
│  │         Per-Agent Prompt                 │                    │
│  │  system.md + schema + agents/sql.md     │                    │
│  └─────────────────────────────────────────┘                    │
│                                                                 │
│  Guardrails run BEFORE and AFTER agent execution                │
│  ┌──────────────┐              ┌──────────────┐                 │
│  │  scope.md    │   ────────►  │ sql_safety.md│                 │
│  │  (pre-check) │              │ (post-check) │                 │
│  └──────────────┘              └──────────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Prompt Files Structure

```
prompts/
├── system.md              # Global rules (privacy, defaults, output style)
├── schema_context.md      # Schema + query constraints
├── guardrails/
│   ├── scope.md           # In/out of scope definitions
│   └── sql_safety.md      # SQL validation + k-anonymity rules
└── agents/
    ├── definition.md      # Definition agent prompt
    ├── sql.md             # SQL agent prompt
    ├── quality.md         # Data quality agent prompt
    └── explanation.md     # Explanation agent prompt
```

---

## Agent Pipeline

The main execution flow from question to answer.

```
User Question
     │
     ▼
┌─────────────┐
│ Scope Guard │ ──(off-topic)──► Reject with helpful message
└─────────────┘
     │ (valid)
     ▼
┌─────────────┐
│   Router    │  Classify intent, select agents
└─────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    AGENT EXECUTION                           │
│                                                             │
│  ┌────────────────┐                                         │
│  │ Definition     │  Interpret question → structured def    │
│  │ Agent          │                                         │
│  └───────┬────────┘                                         │
│          │                                                  │
│          ▼                                                  │
│  ┌────────────────┐                                         │
│  │ SQL Agent      │  Generate + execute SQL                 │
│  │ (with Value    │                                         │
│  │  Discovery)    │                                         │
│  └───────┬────────┘                                         │
│          │                                                  │
│          ▼                                                  │
│  ┌────────────────┐                                         │
│  │ Data Quality   │  Validate results + privacy             │
│  │ Agent          │                                         │
│  └───────┬────────┘                                         │
│          │                                                  │
│          ▼                                                  │
│  ┌────────────────┐                                         │
│  │ Explanation    │  Generate business insights             │
│  │ Agent          │                                         │
│  └────────────────┘                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────┐
│  Response   │  Summary + insights + data + follow-ups
└─────────────┘
```

---

## SQL Agent Flow

The SQL Agent includes a Value Discovery step before query generation.

```
                         SQL Agent
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    VALUE DISCOVERY                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Date Range Discovery                                    │
│     ┌────────────────────────────────────────┐              │
│     │ SELECT MIN(event_date), MAX(event_date)│              │
│     │ FROM events                            │              │
│     └────────────────────────────────────────┘              │
│     Result: 2024-01-02 to 2024-03-31 (65 days)             │
│                                                             │
│  2. Column Value Discovery (per categorical column)         │
│     ┌────────────────────────────────────────┐              │
│     │ SELECT DISTINCT column, COUNT(*)       │              │
│     │ FROM events                            │              │
│     │ WHERE event_date >= (MAX - 90 days)    │  ← Time-bound│
│     │ GROUP BY column                        │              │
│     │ ORDER BY COUNT(*) DESC                 │              │
│     │ LIMIT 50                               │  ← Safe limit│
│     └────────────────────────────────────────┘              │
│                                                             │
│  Discovered Values:                                         │
│  • event_type: money_movement, fee, interest, account_status│
│  • channel: DIGITAL, BRANCH, BATCH                          │
│  • product_type: CHEQUING, SAVINGS                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    SQL GENERATION                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LLM receives:                                              │
│  • Composed prompt (system + schema + agent)                │
│  • Definition from Definition Agent                         │
│  • Discovered values context                                │
│  • Privacy rules (k-anonymity threshold)                    │
│                                                             │
│  LLM generates:                                             │
│  • SQL query using correct enum values                      │
│  • HAVING clause for k-anonymity                            │
│  • Explanation of query logic                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    VALIDATION                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SQL Guard checks:                                          │
│  ☑ SELECT-only (no INSERT/UPDATE/DELETE)                   │
│  ☑ No forbidden columns (customer_id, account_id)          │
│  ☑ No dangerous patterns (injection, comments)             │
│  ☑ LIMIT clause present                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXECUTION                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  DuckDB executes query on CSV data                          │
│  Returns: data, columns, row_count                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Privacy Filtering

How k-anonymity is enforced throughout the pipeline.

```
┌─────────────────────────────────────────────────────────────┐
│                    PRIVACY FLOW                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  THRESHOLD: 10 distinct accounts/customers per bucket       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ SQL Generation                                       │    │
│  │                                                     │    │
│  │ Generated SQL includes:                             │    │
│  │ HAVING COUNT(DISTINCT account_id) >= 10            │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                       │                                     │
│                       ▼                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Query Execution                                      │    │
│  │                                                     │    │
│  │ Buckets with < 10 accounts are filtered out        │    │
│  │ Only privacy-safe aggregations returned            │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                       │                                     │
│           ┌───────────┴───────────┐                         │
│           │                       │                         │
│           ▼                       ▼                         │
│  ┌─────────────────┐     ┌─────────────────┐                │
│  │ Data Returned   │     │ No Data (empty) │                │
│  │ (>= 10 accounts)│     │ (< 10 accounts) │                │
│  └────────┬────────┘     └────────┬────────┘                │
│           │                       │                         │
│           ▼                       ▼                         │
│  ┌─────────────────┐     ┌─────────────────┐                │
│  │ Data Quality    │     │ Data Quality    │                │
│  │ Agent: PASS     │     │ Agent: detects  │                │
│  │                 │     │ k-anonymity     │                │
│  │ Shows data with │     │ filtering       │                │
│  │ unique_accounts │     │                 │                │
│  │ column          │     │ Returns helpful │                │
│  └─────────────────┘     │ privacy message │                │
│                          └─────────────────┘                │
│                                                             │
│  Example Output (data returned):                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ | channel | total_deposits | unique_accounts |      │    │
│  │ |---------|----------------|-----------------|      │    │
│  │ | DIGITAL | 120,050        | 12              |      │    │
│  │ | BRANCH  | (filtered)     | 8 (< 10)        |      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Example Output (privacy message):                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ "This breakdown cannot be shown due to privacy      │    │
│  │  protection requirements. The requested data exists │    │
│  │  but involves too few accounts to report safely."   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## RAG Pipeline

Retrieval-Augmented Generation enhances agent responses with relevant context.

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INDEXING (One-time)                                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                                                         │    │
│  │  knowledge.json ──┐                                     │    │
│  │                   │    ┌──────────────┐                 │    │
│  │                   ├───►│   Chunker    │                 │    │
│  │                   │    │  (by type)   │                 │    │
│  │  schema.json ─────┘    └──────┬───────┘                 │    │
│  │                               │                         │    │
│  │                               ▼                         │    │
│  │                    ┌──────────────────┐                 │    │
│  │                    │ OpenAI Embeddings│                 │    │
│  │                    │ text-embedding-  │                 │    │
│  │                    │ 3-small          │                 │    │
│  │                    └────────┬─────────┘                 │    │
│  │                             │                           │    │
│  │                             ▼                           │    │
│  │                    ┌──────────────────┐                 │    │
│  │                    │    ChromaDB      │                 │    │
│  │                    │  (Persistent)    │                 │    │
│  │                    └──────────────────┘                 │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  RETRIEVAL (Per-query)                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                                                         │    │
│  │  User Question                                          │    │
│  │       │                                                 │    │
│  │       ▼                                                 │    │
│  │  ┌──────────────────┐                                   │    │
│  │  │ Embed Question   │                                   │    │
│  │  └────────┬─────────┘                                   │    │
│  │           │                                             │    │
│  │           ▼                                             │    │
│  │  ┌──────────────────────────────────────┐               │    │
│  │  │         ChromaDB Search              │               │    │
│  │  │                                      │               │    │
│  │  │  ┌────────────┐   ┌────────────┐    │               │    │
│  │  │  │ knowledge  │   │  schema    │    │               │    │
│  │  │  │ collection │   │ collection │    │               │    │
│  │  │  └─────┬──────┘   └─────┬──────┘    │               │    │
│  │  │        │                │           │               │    │
│  │  │        ▼                ▼           │               │    │
│  │  │     Top-K           Top-K           │               │    │
│  │  │    chunks          chunks           │               │    │
│  │  │                                      │               │    │
│  │  └──────────────────────────────────────┘               │    │
│  │           │                                             │    │
│  │           ▼                                             │    │
│  │  ┌──────────────────┐                                   │    │
│  │  │ Format Context   │  → ### Retrieved Knowledge        │    │
│  │  │ for LLM Prompt   │  → ### Retrieved Schema Info      │    │
│  │  └────────┬─────────┘                                   │    │
│  │           │                                             │    │
│  │           ▼                                             │    │
│  │       Agent LLM Call (augmented prompt)                 │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Chunking Strategy

```
knowledge.json → Chunks
├── Glossary Terms
│   ├── "Product Term: Chequing Account\nDefinition: ..."
│   └── "Business Term: Net Flow\nDefinition: ..."
├── Metrics
│   ├── "Metric: Total Deposits\nCategory: volume\nSQL: ..."
│   └── "Metric: Digital Adoption Rate\nCategory: channel\nSQL: ..."
├── SQL Patterns
│   └── "SQL Pattern: daily_summary\nDescription: ...\nExample SQL: ..."
├── Business Rules
│   └── "Business Rule: Withdrawals are negative..."
└── Question Mappings
    └── "Question Pattern: How much money was deposited?\nFilters: ..."

schema.json → Chunks
├── Table Overview
│   └── "Table: sample_events\nDescription: Event-level transactional..."
├── Query Hints
│   └── "Query Guidelines for sample_events:\n- Default time grain: month..."
├── Columns
│   ├── "Column: event_type\nType: STRING\nCategorical: Yes\nValues: ..."
│   └── "Column: event_amount\nType: NUMERIC\nDescription: ..."
├── Enum Values
│   └── "Enum Value: event_type = 'money_movement'\nMeaning: Deposits..."
└── Notes
    └── "Schema Note: Negative amounts: Withdrawals and payments..."
```

### Collection Structure

```
data/chroma_db/
├── knowledge/                    # Knowledge collection
│   ├── glossary chunks           # ~6 chunks
│   ├── metric chunks             # ~10 chunks
│   ├── sql_pattern chunks        # ~4 chunks
│   ├── business_rule chunks      # ~4 chunks
│   └── question_mapping chunks   # ~7 chunks
│
├── schema/                       # Schema collection
│   ├── table_overview chunks     # ~1 chunk
│   ├── query_hints chunks        # ~1 chunk
│   ├── column chunks             # ~10 chunks
│   ├── enum chunks               # ~15 chunks
│   └── note chunks               # ~4 chunks
│
└── query_history/                # History collection (for similarity)
    └── question embeddings       # Growing over time
```

### Agent RAG Integration

```
┌───────────────────────────────────────────────────────────────────┐
│                    AGENT RAG USAGE                                 │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Definition Agent                                                 │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │ retrieve_for_definition(question)                        │      │
│  │   → k=5 knowledge (glossary, metrics)                   │      │
│  │   → k=2 schema (columns, hints)                         │      │
│  │                                                         │      │
│  │ Use case: Map "net flow" → business definition          │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                   │
│  SQL Agent                                                        │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │ retrieve_for_sql(question)                               │      │
│  │   → k=3 knowledge (SQL patterns, metrics)               │      │
│  │   → k=5 schema (columns, enums, types)                  │      │
│  │                                                         │      │
│  │ Use case: Get correct SQL syntax, column types          │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                   │
│  History Search (for similar past queries)                        │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │ find_similar(question, k=3, min_similarity=0.5)          │      │
│  │   → Search query_history collection                     │      │
│  │   → Return successful past queries                      │      │
│  │                                                         │      │
│  │ Use case: Learn from previous high-rated answers        │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### LangChain Integration

```
┌───────────────────────────────────────────────────────────────────┐
│                    LANGCHAIN COMPONENTS                            │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  LLM Abstraction                                                  │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │ from langchain_openai import ChatOpenAI, OpenAIEmbeddings│      │
│  │                                                         │      │
│  │ ChatOpenAI(model="gpt-4o-mini")   # Chat completions    │      │
│  │ OpenAIEmbeddings(model="text-embedding-3-small")        │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                   │
│  Prompt Templates                                                 │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │ from langchain_core.prompts import ChatPromptTemplate   │      │
│  │                                                         │      │
│  │ template = ChatPromptTemplate.from_messages([           │      │
│  │     ("system", "{system_prompt}"),                      │      │
│  │     ("human", "Context:\n{context}\n\nQuestion: {q}")  │      │
│  │ ])                                                      │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                   │
│  Vector Store                                                     │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │ from langchain_chroma import Chroma                     │      │
│  │                                                         │      │
│  │ ChromaDB with persistent storage at data/chroma_db/     │      │
│  │ Collections: knowledge, schema, query_history           │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## File Structure Overview

```
agentic-analytics-orchestrator/
│
├── prompts/                    # Centralized prompt management
│   ├── system.md               # Global rules
│   ├── schema_context.md       # Schema constraints
│   ├── guardrails/
│   │   ├── scope.md            # Scope definitions
│   │   └── sql_safety.md       # SQL safety rules
│   └── agents/
│       ├── definition.md
│       ├── sql.md
│       ├── quality.md
│       └── explanation.md
│
├── src/
│   ├── apps/                   # Demo & automation scripts
│   │   ├── run_demo.py         # Terminal demo runner (13 scenarios)
│   │   ├── streamlit_app.py    # Web UI for interactive demos
│   │   └── ...                 # Other automation scripts
│   │
│   ├── config/
│   │   ├── settings.py         # Environment config
│   │   ├── llm.py              # LLM client
│   │   └── prompts.py          # Prompt loader & composer
│   │
│   ├── orchestrator/
│   │   ├── graph.py            # LangGraph state machine
│   │   ├── router.py           # Intent classification
│   │   └── state.py            # Shared state schema
│   │
│   ├── specialists/
│   │   ├── definition_agent/   # Question interpretation (+ RAG)
│   │   ├── sql_agent/          # SQL generation + value discovery (+ RAG)
│   │   ├── data_quality_agent/ # Result validation + privacy
│   │   └── explanation_agent/  # Business insights
│   │
│   ├── rag/                    # RAG: Retrieval-Augmented Generation
│   │   ├── embedder.py         # OpenAI text embeddings
│   │   ├── vector_store.py     # ChromaDB vector storage
│   │   ├── indexer.py          # Index knowledge & schema
│   │   └── retriever.py        # Query vectors for context
│   │
│   ├── tools/
│   │   ├── duckdb_tool.py      # SQL execution
│   │   └── schema_tool.py      # Schema/knowledge loading
│   │
│   └── guardrails/
│       ├── scope_guard.py      # Topic filtering
│       └── sql_guard.py        # SQL validation
│
├── data/
│   ├── sample_events.csv       # Sample data (Jan-Mar 2024)
│   ├── schema.json             # Column definitions
│   ├── knowledge.json          # Business glossary
│   ├── chroma_db/              # Vector database (auto-generated)
│   └── query_logs.db           # SQLite query history
│
├── docs/
│   ├── ARCHITECTURE.md         # Design documentation
│   ├── ROADMAP.md              # Phase planning
│   └── DIAGRAMS.md             # This file
│
├── logs/                       # Query session logs (JSON)
│
└── main.py                     # Entry point
```

---

## Logging & Evaluation

The system tracks every query for improvement and confidence estimation.

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOGGING & EVALUATION FLOW                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 1. Session Start                                         │    │
│  │    • Generate unique session_id                          │    │
│  │    • Record timestamp, question                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 2. Agent Execution (with tracing)                        │    │
│  │    • Log each agent start/complete                       │    │
│  │    • Track duration, tokens, errors                      │    │
│  │    • Capture input/output summaries                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 3. Self-Evaluation                                       │    │
│  │    Compute confidence scores:                            │    │
│  │    • sql_valid (15%)    - Query generated correctly?     │    │
│  │    • sql_executed (20%) - Ran without errors?            │    │
│  │    • has_data (20%)     - Returned results?              │    │
│  │    • quality_passed (15%) - Passed quality checks?       │    │
│  │    • explanation_present (15%) - Good explanation?       │    │
│  │    • no_errors (15%)    - Pipeline error-free?           │    │
│  │                                                          │    │
│  │    Overall Score → Confidence (low/medium/high)          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 4. User Feedback (optional)                              │    │
│  │    • Rating: 1-5 stars or 👍/👎                          │    │
│  │    • Optional text feedback                              │    │
│  │    • Stored for analysis                                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 5. Persistent Storage (SQLite)                           │    │
│  │    • Query text + embeddings (future similarity search)  │    │
│  │    • Definition, SQL, results                            │    │
│  │    • Self scores + user scores                           │    │
│  │    • Agent traces                                        │    │
│  │    • Performance metrics                                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Query Log Database Schema

```
query_logs
├── id (TEXT)                   # Session UUID
├── question (TEXT)             # User's question
├── question_embedding (BLOB)   # For similarity search (future)
├── definition_json (TEXT)      # Definition agent output
├── sql_query (TEXT)            # Generated SQL
├── result_summary_json (TEXT)  # Query results (truncated)
├── final_response (TEXT)       # Complete response
├── agent_traces_json (TEXT)    # Per-agent execution logs
│
├── self_score (REAL)           # Overall self-evaluation (0-100)
├── self_scores_json (TEXT)     # Detailed breakdown
├── user_score (INTEGER)        # User rating (1-5)
├── user_feedback (TEXT)        # User comments
│
├── latency_ms (REAL)           # Total execution time
├── total_tokens (INTEGER)      # LLM tokens used
├── error_count (INTEGER)       # Number of errors
├── tags (TEXT)                 # Categorization tags
└── created_at (TEXT)           # Timestamp
```

### Confidence Display

```
Self-Evaluation Score → Visual Display

  90-100: ★★★★★ (high confidence)
  70-89:  ★★★★☆ (high confidence)
  50-69:  ★★★☆☆ (medium confidence)
  30-49:  ★★☆☆☆ (low confidence)
  0-29:   ★☆☆☆☆ (low confidence)
```

### Future: History Search Flow

```
                     New Question
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HISTORY SEARCH (Future)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Embed new question                                          │
│  2. Search query_logs for similar embeddings                    │
│  3. If high-confidence match found:                             │
│     • Return cached approach as hint                            │
│     • Show "Similar past query scored X/5"                      │
│  4. Use history to estimate confidence                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Demo System

The project includes 13 enterprise-focused demo scenarios.

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEMO STRUCTURE (13 Scenarios)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Part 1: Core Analytics (SQL + Schema)                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 1. Monthly Net Flow Trend    - Aggregation, privacy      │    │
│  │ 2. Event Volume Overview     - COUNT by month            │    │
│  │ 3. Inflow vs Outflow         - Conditional aggregation   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Part 2: Intent Routing & Knowledge                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 4. Dataset Definition        - Knowledge, no SQL         │    │
│  │ 5. Schema Clarification      - Column explanation        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Part 3: Analytical Explanation                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 6. Trend Interpretation      - SQL + Explanation "why"   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Part 4: Default Assumptions                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 7. Ambiguous Request         - Safe defaults applied     │    │
│  │ 8. "Recent" Activity         - Time interpretation       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Part 5: Governance & Privacy                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 9. Customer Ranking [REFUSE] - PII exposure blocked      │    │
│  │ 10. Account Detail [REFUSE]  - Identifier protection     │    │
│  │ 11. Safe Aggregation         - Privacy-compliant query   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Part 6: Cost & Query Safety                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 12. Large Result Request     - Limit enforcement         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Part 7: End-to-End Pipeline                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 13. Full Pipeline Demo       - Multi-agent, explanation  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Demo Interfaces

```
┌────────────────────────┐     ┌────────────────────────┐
│   Terminal Demo        │     │   Streamlit Web UI     │
│   (run_demo.py)        │     │   (streamlit_app.py)   │
├────────────────────────┤     ├────────────────────────┤
│                        │     │                        │
│  • Automated runs      │     │  • Interactive input   │
│  • CI/CD friendly      │     │  • Visual pipeline     │
│  • Scriptable          │     │  • Demo buttons        │
│  • --interactive mode  │     │  • History tab         │
│                        │     │  • Stats tab           │
│                        │     │  • Shareable           │
└────────────────────────┘     └────────────────────────┘
```

---

## CLI Commands

```bash
# Run a query
python main.py "What is total deposit by channel?"

# Interactive mode with feedback prompts
python main.py -i

# View query history
python main.py --history

# View performance statistics
python main.py --stats

# View improvement insights
python main.py --insights

# Run query without feedback prompt
python main.py "Your question" --no-feedback

# Verbose mode (show trace + score breakdown)
python main.py "Your question" -v

# Demo commands
python src/apps/run_demo.py              # Run all demos
python src/apps/run_demo.py --interactive # Pause between demos
python src/apps/run_demo.py --part 2     # Run specific part
python src/apps/run_demo.py --demo 7     # Run single demo
python src/apps/run_demo.py --list       # List all demos

# Web UI
streamlit run src/apps/streamlit_app.py
```

---

*Last updated: February 2026*
