# CLAUDE.md — Project Instructions & Memory

> This file exists so that anyone (you, me, or a future AI assistant) can pick up
> this project and instantly know **what we are building, why, and the rules we follow.**
> Read this first before doing anything else.

---

## 1. What are we building?

An **Agentic GitHub Issue Solver** — a backend system where you give it a GitHub
issue (a bug report or feature request), and a team of AI "agents" reads the issue,
understands the relevant code, plans a fix, writes the fix, and can open a Pull Request.

Think of it as an automated junior developer.

## 2. Why are we building it?

- **Goal:** A strong, resume-worthy project to help crack a **15+ LPA** job offer.
- It must *demonstrably* use the buzzwords that recruiters and interviewers look for:
  **LangGraph, LangChain, MCP, Agents, Memory, and RAG** — but in a way I can *explain*,
  not just name-drop.
- Every part of this project must be something I can defend in an interview.

## 3. The rules (constraints the user gave — never break these)

| Rule | What it means in practice |
|------|---------------------------|
| **Simple, basic code** | No clever one-liners. Readable, beginner-friendly Python. Comments explain *why*. |
| **End-to-end** | It must actually run start-to-finish: input an issue → get a solution/PR. Not fragments. |
| **Low latency** | Don't make the user wait. Cache, retrieve only what's needed, run things in parallel where possible. |
| **Optimal context window use** | Only feed the LLM the *relevant* code, not the whole repo. Summarize. Trim history. |
| **Token-efficient (don't waste tokens)** | Fewer/cheaper LLM calls, small focused prompts, cache repeated work. Money = tokens. |
| **FastAPI backend** | The system is exposed as a FastAPI web service. |
| **Teach me everything** | For each component, explain *why we need it* and *what it does* — in detail. |
| **Interview-ready** | Capture likely interview questions and answers as we go. |
| **Documentation-first** | Create `.md` files (like `agent.md`, `rag.md`, ...) as we build each part, so I never need to re-ask. |

### Coding conventions (learned from real bugs)
- **No emojis in Python `print()`** — the Windows console uses cp1252 and crashes on them.
  Use `[OK]`, `[DONE]`, `[tool]` etc. Emojis are fine inside `.md` files (UTF-8).
- **Constrain weaker (open) models with strict, step-by-step prompts** — e.g. "one tool
  at a time, never nest tool calls." Don't assume one-shot multi-tool reasoning.
- **Never name files after libraries** (`numpy.py`, `email.py`, `test.py`). They "shadow"
  the real library and break imports machine-wide. (We hit this: a stray `numpy.py` in the
  Python install folder crashed RAG; renamed to `archit_streamlit_hello.py`.)

## 4. How we work (teaching method)

We build like a **student learning step by step**, NOT by dumping the whole codebase:

1. Explain the concept and *why we need it*.
2. Write one small, understandable piece of code.
3. Make sure I understand it (and note interview points).
4. Only then move to the next piece.

Each phase produces a small `.md` note file so knowledge is never lost.

## 5. Tech stack (the "what" and the "why")

| Tool | Why it's here |
|------|---------------|
| **Python** | Beginner-friendly, the default language of AI/LLM tooling. |
| **FastAPI** | Fast, modern Python web framework. Turns our agent into an API. |
| **LangChain** | Toolkit for talking to LLMs, prompts, tools, and RAG building blocks. |
| **LangGraph** | Lets us model the agent as a *graph* (steps + decisions) with state and loops. |
| **MCP (Model Context Protocol)** | A standard way to give the agent real tools (like GitHub) safely. |
| **Vector DB (Chroma/FAISS)** | Stores code as searchable "embeddings" for RAG. |
| **LLM provider (configurable)** | The LLM "brain". **Default while learning: Ollama (local, free).** Switchable to Claude/OpenAI via `.env`. |

### Decisions locked in (2026-07-15)
- **LLM provider:** **Groq** (fast cloud, free tier) for reasoning → chosen for LOW LATENCY. Code stays provider-agnostic (flip to Claude/OpenAI/Ollama via `.env`).
- **Embeddings:** **FastEmbed** (local, free) because Groq has no embedding model. Pattern = local embeddings + cloud reasoning.
- **GitHub access:** Start in **mock/demo mode** (local sample files), add a real GitHub token later.

## 6. Current status / progress

- [x] Phase 0: Foundation docs (this file + ARCHITECTURE.md)
- [ ] Phase 1: Environment setup
- [ ] Phase 2: LangChain basics
- [ ] Phase 3: What is an agent
- [ ] Phase 4: LangGraph basics
- [ ] Phase 5: RAG
- [ ] Phase 6: Memory
- [ ] Phase 7: MCP + GitHub tools
- [ ] Phase 8: Assemble full graph
- [ ] Phase 9: FastAPI backend
- [ ] Phase 10: Optimization + interview prep

> Update the checkboxes above as we finish each phase.
