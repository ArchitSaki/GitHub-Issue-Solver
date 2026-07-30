# langgraph.md — Phase 4: LangGraph (State, Nodes, Edges)

> This is the framework at the center of the project. Master these three words —
> **State, Nodes, Edges** — and you can explain the whole system.

File in this phase: `scripts/phase4_demo.py` (a runnable 3-node graph that branches).

---

## 1. Why LangGraph? (the motivation)

In Phase 3 we hand-wrote an agent loop: a message list, a step counter, a stop check.
That's fine for a toy. A real system also needs:
- **shared state** across many steps (not just a message list),
- **branching** ("if it's a bug do X, if a feature do Y"),
- **loops/retries** ("if the fix failed, try again"),
- structure you can read, test, and draw.

Writing all that by hand becomes spaghetti. **LangGraph** lets you *describe* the flow
as a graph and runs it for you — with state, branching, loops, retries, and streaming.

> Interview line: *"LangGraph models an agent as a state machine / graph, which makes
> multi-step, branching, looping workflows explicit and reliable instead of tangled code."*

## 2. The 3 pieces (this is the whole framework)

### STATE — the shared notebook
A single object passed through the whole graph. Every node reads it and returns updates.
```python
class IssueState(TypedDict):
    issue_text: str
    summary: str
    is_bug: bool
    plan: str
```
Think of it as the memory of the current run. In our architecture doc, this is the
"notebook passed from worker to worker."

### NODES — the workers
A node is just a **function**: it takes the state and returns a dict of the keys it
wants to change. **You never mutate state directly** — you return an update and
LangGraph merges it.
```python
def understand(state) -> dict:
    ...
    return {"summary": ..., "is_bug": ...}   # only the keys we changed
```

### EDGES — the wiring
Edges connect nodes. Two kinds:
- **Normal edge:** always go A → B. `builder.add_edge("bugfix", END)`
- **Conditional edge:** run a *router* function that returns a label deciding where to
  go next. This is how the graph BRANCHES.
```python
builder.add_conditional_edges("understand", route_by_type,
                              {"bugfix": "bugfix", "feature": "feature"})
```
`START` and `END` are special built-in markers for entry and exit.

## 3. Our mini graph (picture)

```
        START
          │
          ▼
     ┌─────────┐
     │understand│  (LLM: summary + is_bug + keywords)
     └────┬────┘
          │  route_by_type(state)   ← conditional edge (the router)
     is_bug?│
      ┌─────┴─────┐
      ▼           ▼
  ┌───────┐   ┌────────┐
  │bugfix │   │feature │   (LLM writes the right kind of plan)
  └───┬───┘   └───┬────┘
      └─────┬─────┘
            ▼
           END
```

Run output proved it: `understand` → (is_bug=True) → `bugfix` → END. The `feature`
node never ran. The graph chose the path itself.

## 4. How to build & run a graph (the recipe)

```python
builder = StateGraph(IssueState)      # 1. create with the state type
builder.add_node("understand", understand)   # 2. register nodes
builder.add_edge(START, "understand")        # 3. wire edges
builder.add_conditional_edges(...)           #    (branch)
graph = builder.compile()                     # 4. compile -> runnable
graph.invoke({"issue_text": "..."})           # 5. run: returns final state
```

## 5. Concepts you'll meet soon (previews)

- **Reducers:** by default a returned key *replaces* the old value. For things like a
  growing message list you want to *append*, not replace. You declare that with an
  annotated field, e.g. `messages: Annotated[list, add_messages]`. We'll use this in
  Phase 8. (Interview: "reducers control how state updates merge.")
- **Loops:** a conditional edge can point *back* to an earlier node → that's a retry loop
  (e.g. "review failed → go back to write_fix"). Add a counter in state to cap retries.
- **Checkpointing / persistence:** LangGraph can save state between steps (a "checkpointer"),
  which gives you pause/resume and memory across runs. Foundation for Phase 6 memory.
- **Prebuilt agent:** `create_react_agent(llm, tools)` builds the Phase-3 loop as a graph
  for you. We now understand what's inside it.

## 6. How the "rules" apply here

- **Low latency / tokens:** branching means we only run the nodes we need (we didn't run
  the feature node at all). Independent nodes can even run in parallel.
- **Simple code:** each node is a tiny, testable function. Easy to read and debug.
- **Optimal context:** each node builds its own small prompt from just the state fields it
  needs — not one giant mega-prompt.

## 7. Interview questions you can now answer

- **Q: What is LangGraph and why use it over a plain loop or chain?**
  A framework to build agents as graphs/state machines. It makes multi-step, branching,
  looping, stateful workflows explicit and robust, with persistence and streaming — hard
  to do cleanly with ad-hoc loops or linear chains.
- **Q: What are nodes, edges, and state?**
  State = shared data passed through the run. Nodes = functions that read state and return
  updates. Edges = transitions between nodes; conditional edges route based on a function.
- **Q: How does branching work?**
  A conditional edge runs a router function that returns a label; the graph follows the
  mapping from label → next node.
- **Q: How do you implement a retry loop?**
  Point a conditional edge from a "verify" node back to the "fix" node, guarded by a retry
  counter in the state so it can't loop forever.
- **Q: LangChain vs LangGraph?**
  LangChain = building blocks (LLMs, prompts, tools, RAG) and linear chains. LangGraph =
  orchestration layer for stateful, cyclic, multi-actor workflows built from those blocks.

✅ Phase 4 done when `python -m scripts.phase4_demo` prints a branch decision + a plan.
