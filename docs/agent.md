# agent.md — Phase 3: What is an Agent? (the ReAct loop)

> This is THE concept of the whole project. If you understand this page deeply,
> you can defend the word "agentic" in any interview.

File in this phase: `scripts/phase3_demo.py` (a hand-written agent loop).

---

## 1. LLM vs Agent (say this in interviews)

| | Plain LLM call | Agent |
|--|----------------|-------|
| Input | text | a goal |
| Can it act on the world? | No — only outputs text | Yes — it can call **tools** |
| How many steps? | one | a **loop** of many steps |
| Who decides the steps? | you (hard-coded) | the **model** decides at runtime |

> **One-liner:** *"An agent is an LLM placed in a loop, given tools, that decides
> which tool to call and when, until the goal is met."*

## 2. The ReAct loop (Reason + Act)

This is the engine inside every agent:

```
        ┌──────────────────────────────────────────┐
        │                                          │
        ▼                                          │
   [REASON]  model thinks: "what should I do next?"│
        │                                          │
        ▼                                          │
   does it want a tool? ──── no ───► [FINAL ANSWER]│  (loop ends)
        │ yes                                      │
        ▼                                          │
   [ACT]  we run the requested tool                │
        │                                          │
        ▼                                          │
   [OBSERVE]  give the tool's result back ─────────┘
```

In `phase3_demo.py` you can literally watch this: the model first calls `add(3,4)`,
gets `7`, then calls `multiply(7,5)`, gets `35`, then writes the final answer.

## 3. What is a "tool"?

A tool is just a **Python function the model is allowed to call**. Two parts matter:

```python
@tool
def add(a: int, b: int) -> int:
    """Add two numbers together and return the sum."""   # <- the model READS this
    return a + b
```

- The **docstring** tells the model what the tool does and when to use it. Write it
  like an instruction, not a code comment. Bad docstring = model misuses the tool.
- The **type hints** (`a: int`) tell the model what arguments to pass.

`llm.bind_tools([add, multiply])` advertises the tools to the model. The model then
replies with `tool_calls` (a request like `add(a=3, b=4)`) instead of final text.
**We** execute the function and hand the result back as a `ToolMessage`.

> Important: the LLM never runs your code itself. It only *asks* to. Your loop runs
> it and returns the answer. (Security point: you control what tools exist = safety.)

## 4. How this maps to our GitHub project

In the real system, the agent's tools will be things like:
- `search_code(query)` — RAG lookup (Phase 5)
- `read_file(path)` — read a repo file (Phase 7, via MCP/GitHub)
- `open_pull_request(...)` — create the fix (Phase 7)

Same loop, real tools: *reason about the issue → read the right files → write a fix → open a PR.*

## 5. Why we hand-wrote the loop (and what changes later)

We wrote the loop manually so it's not magic. In Phase 4+ **LangGraph gives us this
loop for free** (`create_react_agent`, or our own graph), plus retries, branching,
and state. But now you know exactly what's inside that helper.

## 6. Token / latency notes (your rules)

- **Cap the loop** (`max_steps`) so a confused agent can't call tools forever = runaway cost.
- **Fewer, sharper tools** beat many vague tools (less confusion, fewer wasted steps).
- **Short tool results**: return only what's needed (e.g. a code snippet, not a whole file)
  — every tool result goes back into the context window and costs tokens.

## 7. Interview questions you can now answer

- **Q: What makes a system "agentic"?**
  An LLM that autonomously decides and takes actions (tool calls) in a loop toward a
  goal, using observations to guide next steps — not a fixed, pre-scripted pipeline.
- **Q: Explain the ReAct pattern.**
  Reason → Act (tool call) → Observe (result) → repeat until done. It interleaves
  thinking with acting so the model can gather info before deciding.
- **Q: How does the model actually "use" a tool?**
  Via tool/function calling: we advertise tools with `bind_tools`; the model returns a
  structured tool-call request; our runtime executes it and returns the result as a
  ToolMessage; the model continues.
- **Q: How do you keep an agent safe / bounded?**
  Whitelist the tools it has, cap the number of steps, validate tool arguments, and
  keep tool results small. The model can only do what its tools allow.
- **Q: Single agent vs multi-agent?**
  Single = one LLM+tools loop. Multi-agent = several specialized agents (e.g. planner,
  coder, reviewer) coordinated — which is exactly what LangGraph lets us orchestrate next.

## 8. Two REAL bugs we hit in Phase 3 (great interview stories)

### Bug 1: `tool_use_failed` — the model nested tool calls
The model tried `multiply(5, add(3,4))` in ONE call. Tool arguments must be plain
values, not another pending tool call, so Groq rejected it.
- **Root cause:** smaller open models (Llama) are weaker at tool-calling discipline.
- **Fix:** an explicit system prompt — "one tool at a time, never nest, compute the
  inner result first, then the outer." This forces proper ReAct behaviour.
- **Lesson (say this in interviews):** *"Model capability varies; I constrain weaker
  models with strict prompting and a step-by-step loop instead of expecting one-shot
  multi-tool reasoning."*

### Bug 2: `UnicodeEncodeError` on Windows console
Printing a `✅` emoji crashed because the Windows terminal uses cp1252, not UTF-8.
- **Fix / project rule:** keep `print()` output plain ASCII (use `[OK]`, `[DONE]`).
  Emojis are fine inside `.md` files (UTF-8), just not in console prints on Windows.

## 9. What "for free" LangGraph gives us next (Phase 4 preview)
Our hand-written loop had: a message list, a step cap, tool execution, and stop logic.
LangGraph packages all of that — plus shared State, branching, retries, and streaming —
so we describe the *graph* and it runs the loop. Now you know what's inside the box.

✅ Phase 3 done when `python -m scripts.phase3_demo` shows the add → multiply → final flow.
