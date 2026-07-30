# full_graph.md — Phase 8: The Complete Agentic Pipeline

> Everything you built in Phases 2–7 becomes ONE workflow here.
> Input: an issue number. Output: a reviewed code fix + a pull request.

Files: `app/graph/state.py`, `app/graph/nodes.py`, `app/graph/builder.py`,
`scripts/phase8_demo.py`.

---

## 1. The graph

```
START -> fetch_issue -> understand -> recall_memory -> retrieve_code
                                                           |
                                                           v
                                                       write_fix  <--+
                                                           |         |
                                                           v         | retry
                                                        review ------+
                                                           | approved
                                                           v
                                                 save_memory -> open_pr -> END
```

## 2. Every node, and which phase it reuses

| Node | Job | Reuses |
|------|-----|--------|
| `fetch_issue` | get the issue text | Phase 7 tools |
| `understand` | summary + is_bug + keywords | Phase 2 structured output |
| `recall_memory` | find similar past fixes | Phase 6 long-term memory |
| `retrieve_code` | find the few relevant chunks + target file | Phase 5 RAG |
| `write_fix` | produce the corrected file | Phase 2 LLM |
| `review` | second opinion; approve or reject | LLM self-check → drives the loop |
| `save_memory` | remember this solution | Phase 6 (write side) |
| `open_pr` | ship it | Phase 7 tools |

## 3. The retry loop — why LangGraph earns its place

`review -> write_fix` is a **cycle**. A plain LangChain chain is a straight line and
cannot do this. The graph can:
- if the reviewer **rejects**, the notes go back into the next `write_fix` prompt,
- `attempts` is capped by `MAX_ATTEMPTS` so cost is **bounded**,
- if we hit the cap we ship the best attempt rather than looping forever.

> Interview line: *"The reviewer node closes a feedback loop back into the writer,
> with a bounded retry counter — self-correction with a hard cost ceiling."*

This is the **generator–critic pattern** (a.k.a. reflection): one LLM produces, another
critiques. It measurably improves output quality over a single-shot generation.

## 4. Token & context discipline in this design

- The State holds **small structured fields**, not a growing chat transcript.
  Each node builds a tiny prompt from only the fields it needs.
- `retrieve_code` sends a handful of RAG chunks, never the repo.
- `understand` runs once and everything downstream reuses its `summary`.
- Tool outputs are truncated (`read_repo_file` caps at 4000 chars).
- Retries are capped at `MAX_ATTEMPTS = 2`.

## 5. A REAL bug we hit: JSON can't hold source code

First version used `with_structured_output(Fix)` to return `{target_file, fixed_code}`.
It crashed with `tool_use_failed`:
```
"fixed_code": """"Authentication logic for the demo app."""...   <- invalid JSON
```
- **Root cause:** a whole Python file inside a JSON string needs quotes/newlines
  escaped. The file began with a `"""` docstring, which broke the JSON.
- **Fix:** ask for a **markdown code fence** and extract it with `_extract_code()`.
  Plain text needs no escaping.
- **Lesson (engineering judgment):** structured output is ideal for **small scalar
  fields** (bool, short string, list). It is **fragile for large code blobs**. Match the
  output format to the payload.

## 6. Run it

```powershell
python -m scripts.phase8_demo
```
Expected: nodes print in order, `approved=True`, and a patch appears in `.mock_prs/`.

## 7. Interview questions you can now answer

- **Q: Walk me through your system's architecture.**
  A LangGraph state machine: fetch → understand → recall memory → RAG retrieve →
  write fix → review → (retry loop) → save memory → open PR, exposed over FastAPI.
- **Q: Why LangGraph instead of a chain or a single ReAct agent?**
  I need a cycle (review → rewrite), explicit state, and bounded retries. Chains are
  linear; a bare ReAct agent gives less control over the workflow and cost.
- **Q: How do you stop the agent from looping forever?**
  A retry counter in State checked by the router; at `MAX_ATTEMPTS` it exits with the
  best attempt.
- **Q: How do you improve output quality?**
  A generator–critic (reflection) loop: a reviewer node validates the fix and feeds
  rejection notes back into the next attempt.
- **Q: How do you keep it cheap and fast?**
  Small structured State instead of a growing transcript, top-k RAG instead of whole
  files, truncated tool outputs, one `understand` pass reused downstream, capped retries.

✅ Phase 8 done when the demo prints a fix and writes a PR file into `.mock_prs/`.
