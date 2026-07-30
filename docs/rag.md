# rag.md — Phase 5: RAG (Retrieval Augmented Generation)

> The single biggest lever for your "optimal context window / low token" goals.
> RAG = give the LLM only the relevant code, retrieved on demand, instead of the whole repo.

Files: `app/rag/indexer.py`, `app/rag/retriever.py`, `scripts/phase5_demo.py`,
plus the demo codebase in `sample_repo/`.

---

## 1. The problem RAG solves

An LLM has a **context window** — a max amount of text it can read at once. A real repo
is far too big to fit, and even if it fit, sending it all would be **slow and expensive**
(you pay per token). So: how does the agent find the *few* relevant files for an issue?

**Answer: RAG.** Pre-index the code; at query time retrieve only the closest chunks.

## 2. What is an "embedding"? (the core idea)

An **embedding** is a list of numbers (a vector) that represents the *meaning* of text.
Texts with similar meaning get vectors that are close together. So "login fails on empty
email" lands near the `login()` code even if they share no exact words. Finding nearby
vectors = **semantic search** (search by meaning, not keywords).

We generate embeddings **locally with FastEmbed** (free; Groq has no embedding model).

## 3. The RAG pipeline (memorize these 4 steps)

```
   INDEX TIME (once, ahead of time)          QUERY TIME (per issue)
   ┌────────────────────────────┐            ┌──────────────────────────┐
   │ 1. LOAD  read code files   │            │ a. embed the question    │
   │ 2. SPLIT into chunks       │            │ b. find nearest chunks   │
   │ 3. EMBED each chunk->vector│            │    (top-k by similarity) │
   │ 4. STORE vectors in Chroma │            │ c. hand them to the LLM  │
   └────────────────────────────┘            └──────────────────────────┘
```

- **indexer.py** does steps 1–4 (`build_index`).
- **retriever.py** does a–c (`search_code`).

## 4. Key knobs and WHY they matter (token/latency)

| Knob | In code | Effect |
|------|---------|--------|
| **chunk_size** (700) | `RecursiveCharacterTextSplitter` | small chunks = focused results, fewer wasted tokens |
| **chunk_overlap** (100) | same | repeats a little text across chunks so we don't cut a function in half |
| **top_k** (`RAG_TOP_K=4`) | `search_code(k=...)` | how many chunks we retrieve. Higher = more context but more tokens. Tune it. |
| **metadata `source`** | in `_load_files` | lets us tell the LLM WHICH file a snippet is from (needed to write the fix/PR) |

> **The RAG trade-off (great interview answer):** too small top_k → you miss the needed
> code (low recall); too big → you waste tokens and add noise (and can dilute the answer).
> You tune top_k + chunk_size to balance recall vs cost.

## 5. Why "Augmented Generation"?

We *augment* the LLM's prompt with *retrieved* facts, then it *generates* the answer.
The LLM stays general; the fresh, specific knowledge comes from retrieval. Benefits:
- **No retraining** needed to know your codebase — just index it.
- **Up to date** — re-index and it knows the new code.
- **Grounded** — answers cite real files, reducing hallucination.

## 6. A REAL bug we hit: module shadowing (excellent interview story)

RAG import crashed with a weird error: `import numpy` was loading a file named
`numpy.py` that lived in the Python install folder (an old Streamlit practice script),
which tried to `import streamlit` and failed.
- **Root cause:** Python imports the FIRST module it finds on `sys.path` with that name.
  A user file named `numpy.py` **shadowed** the real NumPy library for the whole machine.
- **Fix:** rename the stray file (we renamed it to `archit_streamlit_hello.py`) and clear
  its `__pycache__`.
- **Lesson:** never name your own files after libraries (`numpy.py`, `email.py`,
  `queue.py`, `test.py`...). It silently breaks imports everywhere.

## 7. Run it

```powershell
python -m scripts.phase5_demo
```
Expected: it indexes `sample_repo`, then a login query ranks `auth.py` first.
(First run downloads the ~90MB FastEmbed model — one time only.)

## 8. Interview questions you can now answer

- **Q: What is RAG and why use it?**
  Retrieval Augmented Generation: retrieve relevant documents and add them to the prompt
  so the LLM answers grounded in your data — without retraining, always current, less
  hallucination, and far cheaper than stuffing everything into context.
- **Q: What's an embedding / vector search?**
  An embedding is a numeric vector capturing meaning; similar meanings → nearby vectors.
  We embed the query and find the nearest stored chunks (semantic search).
- **Q: Why chunk documents? How do you pick chunk size / overlap / top-k?**
  Chunking keeps retrieved context focused and cheap. Size/overlap/top-k are tuned to
  balance recall (finding the right code) vs. token cost and noise.
- **Q: What is a vector database (Chroma)?**
  A store optimized for saving embeddings and doing fast nearest-neighbor search over them.
- **Q: How does RAG reduce cost/latency?**
  It sends only a few relevant chunks instead of the whole corpus → fewer input tokens →
  cheaper and faster, while fitting the context window.

✅ Phase 5 done when `scripts/phase5_demo.py` builds the index and ranks `auth.py` on top.
