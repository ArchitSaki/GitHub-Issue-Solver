# ARCHITECTURE.md — The High-Level Design

> Read this to understand the "big picture" before touching any code.
> We will build every box in this diagram, one phase at a time.

---

## 1. The one-sentence idea

> A user sends a **GitHub issue** to our **FastAPI** server. Inside, a **LangGraph**
> workflow coordinates **agents** that use **RAG** (to find relevant code), **memory**
> (to remember past work), and **MCP tools** (to actually talk to GitHub), and produces
> a **fix / Pull Request**.

## 2. The picture (data flow)

```
                        ┌─────────────────────────────────────────────┐
                        │                 USER / CLIENT                │
                        │   "Solve issue #42 in repo owner/project"    │
                        └───────────────────────┬─────────────────────┘
                                                │ HTTP POST /solve
                                                ▼
                        ┌─────────────────────────────────────────────┐
                        │              FastAPI  (app/main.py)          │
                        │   - validates input   - starts the workflow  │
                        └───────────────────────┬─────────────────────┘
                                                │ invoke(state)
                                                ▼
        ┌───────────────────────────────────────────────────────────────────────┐
        │                     LANGGRAPH  WORKFLOW  (the brain)                    │
        │                                                                         │
        │   [1] FETCH ISSUE ──► [2] UNDERSTAND ──► [3] RETRIEVE CODE (RAG)        │
        │                                              │                          │
        │                                              ▼                          │
        │        [6] OPEN PR ◄── [5] REVIEW/VERIFY ◄── [4] PLAN & WRITE FIX       │
        │                                                                         │
        │   State (shared notebook) flows through every step.                     │
        └───────┬───────────────────┬────────────────────┬──────────────────────┘
                │                   │                     │
                ▼                   ▼                     ▼
        ┌──────────────┐    ┌──────────────┐     ┌──────────────────┐
        │   RAG layer  │    │  Memory layer│     │   MCP / GitHub    │
        │ vector DB of │    │ short + long │     │  tools: read repo,│
        │ the codebase │    │ term recall  │     │  comment, open PR │
        └──────────────┘    └──────────────┘     └──────────────────┘
                │                                          │
                ▼                                          ▼
        ┌──────────────┐                          ┌──────────────────┐
        │  Embeddings  │                          │   GitHub API      │
        │   + LLM      │                          │  (real world)     │
        └──────────────┘                          └──────────────────┘
```

## 3. What each box is, and WHY we need it

### FastAPI (the front door)
- **What:** A web server exposing endpoints like `POST /solve`.
- **Why:** Turns our agent into a real product other apps can call. Interviewers want to
  see you can *serve* a model, not just run it in a notebook. It's async → good for latency.

### LangGraph workflow (the brain / orchestrator)
- **What:** A *graph* of steps (nodes) connected by edges. A shared `State` object is
  passed along and updated by each node. It can loop (retry) and branch (make decisions).
- **Why:** Real agent work isn't a straight line — it needs "if the fix fails, try again",
  "if issue unclear, ask for more info". A graph models this cleanly. Plain function calls
  can't easily loop/branch with shared memory. **This is the centerpiece of the project.**

### Agents (the workers)
- **What:** An LLM given a goal + a set of tools, that decides *which* tool to use and *when*
  in a loop (Reason → Act → Observe → repeat).
- **Why:** The "intelligence". Instead of us hard-coding every step, the agent figures out
  what to do. Different nodes use the LLM in an agentic way (e.g. the "write fix" node).

### RAG — Retrieval Augmented Generation (the memory of the codebase)
- **What:** We chop the repo's code into chunks, turn them into vectors (embeddings), store
  them in a vector DB. At query time we fetch only the chunks relevant to the issue.
- **Why:** An LLM can't fit a whole codebase in its context window, and doing so would be
  slow + expensive (violates our token/latency rules). RAG feeds it **only relevant code**.

### Memory (remembering across steps and across runs)
- **What:** Short-term = the current run's state/history. Long-term = a store of past issues
  we solved and their outcomes, recalled later.
- **Why:** Makes the agent smarter over time and keeps context small (we recall summaries,
  not raw transcripts). Directly serves the "optimal context / token-efficient" rules.

### MCP + GitHub tools (the hands)
- **What:** MCP (Model Context Protocol) is a standard interface for giving an LLM tools.
  We connect a GitHub tool-set so the agent can read files, read the issue, comment, open PRs.
- **Why:** Without tools, the agent can only *talk*. Tools let it *act* on the real world.
  MCP is the modern, standardized way to do this (great interview talking point).

## 4. The single most important concept: **State**

Everything in LangGraph revolves around a shared **State** — think of it as a notebook
passed from worker to worker. Each node reads the notebook, does its job, and writes its
result back. Example fields our State will hold:

```
issue_text        -> the raw issue
issue_summary     -> a short, cleaned-up understanding
relevant_code     -> code chunks RAG found
plan              -> the step-by-step fix plan
patch             -> the actual code change
review_notes      -> did the fix look correct?
pr_url            -> the final output
messages          -> running log (kept SHORT for token efficiency)
```

## 5. How the "rules" show up in the architecture

| Rule | Where it lives |
|------|----------------|
| Low latency | async FastAPI, parallel nodes, cached embeddings |
| Optimal context | RAG retrieves only top-k relevant chunks; we summarize the issue |
| Token-efficient | small prompts, cheap model for easy steps, cache repeated calls |
| Simple code | each node is a small plain Python function |
| End-to-end | FastAPI in → PR out |

## 6. Build order (each is a phase with its own `.md` note)

1. Environment → 2. LangChain basics → 3. Agents → 4. LangGraph →
5. RAG → 6. Memory → 7. MCP/GitHub → 8. Assemble graph → 9. FastAPI → 10. Optimize.

We are intentionally building the *pieces* first and assembling them at the end —
exactly how you'd learn it as a student.
