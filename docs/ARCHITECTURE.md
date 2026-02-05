# Architecture & Flow

This doc provides flowcharts for (1) the overall multi-phase design and (2) Phase 1 (this repo) only.

---

## Design Overview

- **Phase 1 (this repo) = overall analytical agent system.** Goal is to show **how the analytical agent system is designed**: one main Orchestrator coordinating several specialist agents. The **SQL Agent here is simple** (single agent, no nesting). Focus is system design at the analytics layer.

- **Later phases = go deep into sub-agents.** Each phase is a separate repo that deepens one area. In particular, the **SQL agent becomes a multi-agent system** in Phase 2: it acts like a **hub** (orchestrator) with its own **domain specialists** (e.g. Digital Marketing, Transaction, Customer, Campaign). So the pattern is **main orchestrator → hub → sub-hub**: the main orchestrator is the top-level hub; when you "open" the SQL agent, it's a sub-hub with its own orchestrator and specialists. Any such hub is also a sub-agent from the parent's point of view. That pattern can repeat (e.g. RAG or others could become hubs with sub-agents in their phases).

- **Summary:** Phase 1 = one-level design (orchestrator + simple agents). Phase 2+ = selected agents become hubs (orchestrator + their own sub-agents), i.e. hub → sub-hub → … .

---

## 1. Overall Design (All Phases — Hub → Sub-Hub)

Top level: main Orchestrator (Hub). One of its sub-agents, SQL, is deepened in Phase 2 into a **sub-hub** with its own orchestrator and specialists. RAG can be deepened similarly in Phase 3.

**Phase 1 layer (this repo) — parallel agents:**

```
              User Question
                    │
                    ▼
          ┌─────────────────────┐
          │     Orchestrator    │
          │ (intent & routing)  │
          └──────────┬──────────┘
                     │
     ┌───────┬───────┼───────┬───────┐
     │       │       │       │       │
     ▼       ▼       ▼       ▼       ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ Definition │ │    SQL     │ │   Data     │ │ Explanation│ │    RAG     │
│   Agent    │ │   Agent    │ │  Quality   │ │   Agent    │ │   Tool     │
│(metric &   │ │(query &    │ │   Agent    │ │(business   │ │(knowledge  │
│ meaning)   │ │ execution) │ │(validation │ │ insights)  │ │ grounding) │
└────────────┘ └────┬───────┘ └────────────┘ └────────────┘ └────────────┘
                    │
                    │  Phase 2: SQL becomes a sub-hub
                    ▼
          ┌─────────────────────┐
          │  SQL Orchestrator   │
          │ (plan → execute)    │
          └──────────┬──────────┘
                     │
     ┌──────────┼──────────┬──────────┬──────────┐
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Digital  │ │Transaction│ │ Customer │ │ Campaign │
│ Marketing│ │  Agent   │ │  Agent   │ │  Agent   │
│  Agent   │ │          │ │          │ │          │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

- Phase 1: Orchestrator fans out to agents **in parallel** (orchestrator decides which and in what order; conceptually they are parallel specialists).
- Phase 2: The SQL Agent is deepened into a sub-hub (SQL Orchestrator + domain specialists: Digital Marketing, Transaction, Customer, Campaign). RAG can be deepened similarly in Phase 3.

---

## 2. Phase 1 Only (This Repo)

Single level: one Orchestrator, simple specialist agents in **parallel**. No sub-hubs.

```
              User Question
                    │
                    ▼
          ┌─────────────────────┐
          │     Orchestrator    │
          │ (intent & routing)  │
          └──────────┬──────────┘
                     │
     ┌───────┬───────┼───────┬───────┐
     │       │       │       │       │
     ▼       ▼       ▼       ▼       ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ Definition │ │    SQL     │ │   Data     │ │ Explanation│ │    RAG     │
│   Agent    │ │   Agent    │ │  Quality   │ │   Agent    │ │   Tool     │
│(metric &   │ │  (simple)  │ │   Agent    │ │(business   │ │(knowledge  │
│ meaning)   │ │(query &    │ │(validation │ │ insights)  │ │ grounding) │
│            │ │ execution) │ │ & anomaly) │ │            │ │ (optional) │
└────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘
```

- Orchestrator decides **which** agents to call and **in what order**; agents are the parallel specialists below.
- Each agent is **simple** (no nested multi-agent in Phase 1).
- All coordination flows through the Orchestrator; agents do not call each other directly.
- Orchestrator passes context/results to the next agent as needed.
