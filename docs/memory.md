# memory.md — Phase 6: Memory (short-term + long-term)

> Agents need memory the way humans do: a scratchpad for the current task, and
> lasting experience across tasks. Interviewers love "what kinds of memory does
> your agent have?" — this page answers it.

Files: `app/memory/store.py`, `scripts/phase6_demo.py`.

---

## 1. The two kinds of memory (the core distinction)

| | Short-term (working) memory | Long-term memory |
|--|-----------------------------|------------------|
| What | the current run's context | knowledge that survives across runs |
| Where | the message list / LangGraph **State** | a database (here: a vector store) |
| Lives | only while solving ONE issue | forever (persisted to disk) |
| Example | "the issue text + steps so far this run" | "here's how we fixed a similar issue last week" |
| We used it in | Phase 3 agent loop, Phase 4 State | Phase 6 (`LongTermMemory`) |

> One-liner: *"Short-term memory is the working context of the current run;
> long-term memory is persistent experience recalled across runs."*

## 2. How our long-term memory works

It's **RAG over our own past solutions** (same tech as Phase 5, different data):
1. When we solve an issue, we `remember(issue_summary, solution, id)` → stored as an
   embedding in a separate Chroma collection (`past_issues`).
2. When a new issue arrives, we `recall(new_issue)` → semantic search returns the most
   similar past issues **and their fixes**.

The Phase 6 demo proved it: a "blank email" issue recalled an "empty email" fix even
though the words differ — because they mean the same thing.

### Why a SEPARATE store from the code index?
Code chunks (Phase 5) and past solutions (Phase 6) are different kinds of knowledge.
Keeping them in separate collections avoids mixing "here's some code" with "here's a
past fix" during retrieval. Clean separation = better, more predictable recall.

## 3. Why memory serves your project goals

- **Token-efficient / low latency:** if a near-identical issue was solved before, reuse
  the plan instead of re-reasoning from scratch — fewer/cheaper LLM calls.
- **Optimal context:** we store *summaries + solutions*, not giant raw transcripts, so
  what we recall stays small.
- **Smarter over time:** the system accumulates experience; later runs benefit from earlier ones.

## 4. Short-term memory in LangGraph: the "checkpointer" (preview for Phase 8)

LangGraph can persist a run's State with a **checkpointer**:
```python
from langgraph.checkpoint.memory import MemorySaver
graph = builder.compile(checkpointer=MemorySaver())
# now each run has a thread_id; state is saved between steps -> pause/resume,
# and multi-turn conversations that remember earlier turns.
```
- `MemorySaver` = in-RAM (simple, resets on restart). There are durable ones (SQLite/Postgres).
- This is how short-term memory becomes *reliable* (survives crashes, enables human-in-the-loop).

## 5. Bonus: memory vocabulary (sound senior in interviews)

- **Working/short-term memory** — current context window / State.
- **Episodic memory** — specific past events ("we fixed issue #42 like this"). Our
  `LongTermMemory` is basically episodic.
- **Semantic memory** — general facts/knowledge (e.g. project conventions).
- **Procedural memory** — learned skills/procedures (e.g. reusable tool-use recipes).
- **Checkpointing/persistence** — saving State so runs can pause, resume, and be audited.

## 6. Run it

```powershell
python -m scripts.phase6_demo
```
Expected: three past issues saved; a new "blank email" issue recalls the "empty email"
fix as the top match.

## 7. Interview questions you can now answer

- **Q: What types of memory does your agent have?**
  Short-term (the run's State/messages — working context) and long-term (a persistent
  vector store of past issues+fixes, recalled semantically). Optionally episodic vs
  semantic vs procedural framing.
- **Q: How is long-term memory implemented?**
  As RAG over past solutions: embed each solved issue, store it, and semantic-search it
  when a new issue arrives to reuse prior experience.
- **Q: How does LangGraph handle memory/persistence?**
  Via checkpointers that save graph State (in-memory or durable like SQLite/Postgres),
  enabling pause/resume, multi-turn memory, and human-in-the-loop.
- **Q: How does memory reduce cost?**
  Reusing recalled solutions avoids redundant reasoning; storing summaries (not raw logs)
  keeps recalled context small.
- **Q: Memory vs RAG — same thing?**
  Same underlying tech (embeddings + vector search). RAG usually means retrieving external
  knowledge (docs/code); memory means retrieving the agent's own past interactions. We use
  both, in separate stores.

✅ Phase 6 done when `scripts/phase6_demo.py` recalls the empty-email fix for a blank-email issue.
