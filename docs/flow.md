# flow.md — The Complete Journey of One Issue

> **Read this doc if you want the whole picture in one place.**
> Every other doc explains one *piece* (RAG, memory, MCP…). This one follows a single
> issue from the moment it arrives to the moment a pull request exists, in plain words.
>
> We trace a real example: **issue #42** against the real files in `sample_repo/`.

---

## 0. The idea in one sentence

> You give it a bug report. It finds the broken file, writes the corrected file,
> checks its own work, and saves the change as a pull request.

Everything else in this repo is machinery to make those four things happen
**reliably** (it double-checks itself) and **cheaply** (it never reads the whole codebase).

---

## 1. The cast — who does what

| Piece | File | Its job, in plain words |
|---|---|---|
| **Front door** | `app/main.py` | The web API. Takes `{"issue_number": 42}` over HTTP. |
| **Wiring diagram** | `app/graph/builder.py` | Connects the 8 steps with arrows (including one that loops back). |
| **The notebook** | `app/graph/state.py` | The shared scratchpad passed from step to step. |
| **The 8 workers** | `app/graph/nodes.py` | One small function per step. This is where the work happens. |
| **The brain socket** | `app/agents/llm.py` | Hands out the AI model and the embedding model. |
| **The librarian** | `app/rag/indexer.py` + `retriever.py` | Files the code away, then finds the relevant bits. |
| **The diary** | `app/memory/store.py` | Remembers past issues and how they were fixed. |
| **The hands** | `app/tools/github_tools.py` | Read an issue, read a file, open a pull request. |
| **The USB-C plug** | `mcp_server/github_mcp_server.py` | Publishes those same hands over the MCP standard. |

---

## 2. Before anything: INDEX TIME (happens once)

Before we can *search* the code, we have to *file it away*. This runs once, ahead of
time — not during a user's request.

```
sample_repo/               →  read every code file
├── auth.py      737 chars
├── database.py  344 chars
└── utils.py     273 chars
```

**Cut each file into pieces of max 700 characters** (`chunk_size=700`, with a
100-character overlap so we don't slice a function in half and lose the seam):

```
auth.py     (737 chars → too big) → CHUNK 1  +  CHUNK 2
database.py (344 chars → fits)    → CHUNK 3
utils.py    (273 chars → fits)    → CHUNK 4
```

**Turn each chunk into numbers.** An "embedding" is a list of numbers that captures
the *meaning* of text. Two pieces of text about the same thing get similar numbers —
even if they use totally different words. This runs **locally and free** on your
machine (FastEmbed, ~90 MB model).

**Save them in `.vectordb/`** — each chunk stored with a sticky note recording
**which file it came from**. That sticky note is the single most important detail in
this whole document; it is how the agent later knows *which file to fix*.

```
CHUNK 1  [0.21, -0.04, 0.88, ...]   note: "sample_repo\auth.py"
CHUNK 2  [0.19, -0.11, 0.72, ...]   note: "sample_repo\auth.py"
CHUNK 3  [-0.33, 0.51, 0.02, ...]   note: "sample_repo\database.py"
CHUNK 4  [0.05, 0.44, -0.27, ...]   note: "sample_repo\utils.py"
```

> **Vocabulary check:** we retrieve **chunks**, not files. Two of our four chunks come
> from the *same* file.

---

## 3. The issue arrives

```json
{
  "number": 42,
  "title": "App crashes on login with empty email",
  "labels": ["bug", "auth"],
  "body": "When I click the 'Login' button while the email field is empty, the whole
           app crashes with an error instead of showing a friendly validation message.
           Steps: 1) open login page 2) leave email blank 3) click Login.
           Expected: a validation error. Actual: crash."
}
```

The notebook starts almost empty:

```
NOTEBOOK
  issue_number: 42
```

---

## 4. The eight steps

### STEP 1 — `fetch_issue` — go get the bug report

Calls the `get_issue` tool. In **mock mode** it reads `mock_data/issues.json`.
In **real mode** it calls the GitHub REST API.

```
NOTEBOOK
+ issue_text: "Title: App crashes on login with empty email
               Labels: bug, auth
               Body: When I click the 'Login' button while..."
+ attempts:   0
```

---

### STEP 2 — `understand` — boil the paragraph down to three facts

**🤖 AI CALL #1.** We hand the AI the rambling report and ask it to fill in a fixed
shape (a "structured output"): a summary, a type, and some keywords.

```
NOTEBOOK
+ summary:  "Login crashes when the email field is empty"
+ is_bug:   true
+ keywords: ["login", "email", "validation"]
```

**Why this step exists:** from here on, *nobody ever uses the long paragraph again*.
One short line replaces it in every later prompt. One cheap call now saves tokens in
all six remaining steps.

---

### STEP 3 — `recall_memory` — "have we seen this before?"

Searches the diary (`.memorydb/`) for similar past issues.

```
NOTEBOOK
+ past_experience: "(no similar past issues)"
```

On a later run, once the diary has entries, this would say something like:

```
- Past issue: Signup crashed on a blank phone number
  Fix: added an input guard before parsing the value
```

That hint gets pasted into the "write the fix" prompt so the agent reuses what it
already learned instead of re-deriving it from scratch.

---

### STEP 4 — `retrieve_code` — **find WHICH file is broken**

This is the heart of the design.

**4a. Build the search query — and note what we do NOT use.** We do *not* search with
the original bug report. We search with the short version from Step 2:

```
query = summary + keywords
      = "Login crashes when the email field is empty login email validation"
```

The raw report is full of UI noise ("I click the button", "Steps: 1) 2) 3)").
The short version is dense and on-topic, so it matches better. This is called
**query rewriting**.

**4b. Search.** Turn the query into numbers and ask the vector database for the
closest chunks. `RAG_TOP_K=4`, so we get 4 back, ranked:

| Rank | Chunk | From | Why it matched |
|---|---|---|---|
| **1** | Chunk 1 | `auth.py` | contains `login`, `email`, and the crashing line |
| 2 | Chunk 2 | `auth.py` | contains `email` |
| 3 | Chunk 4 | `utils.py` | text helpers — vaguely similar |
| 4 | Chunk 3 | `database.py` | least related |

**4c. Read the sticky note on the winner.** One line decides the whole run:

```python
target = chunks[0]["source"]      # → "sample_repo\auth.py"
```

```
NOTEBOOK
+ target_file:   "sample_repo\auth.py"
+ relevant_code: "--- chunk 1 (from auth.py) --- ..."
```

**Why this is the whole point of RAG here.** An AI model cannot read a 500-file
codebase — it does not fit in its context window, and paying for it every run would be
absurd. So we never send the codebase. We send a *question*, get back *4 chunks*, and
use their sticky notes to pick one file.

> **📏 The scaling point:** `sample_repo/` has exactly 4 chunks and we asked for the
> top 4, so in the demo nothing is actually filtered out — all that happened was
> **ranking**. On a real repo it's 3,000 chunks in, 4 out: **2,996 discarded**.
> The demo proves the plumbing; the savings appear at scale. Either way the AI calls
> stay the same size — **retrieval cost does not grow with repo size.**

---

### STEP 5 — `write_fix` — write the corrected file

We open the **whole** `auth.py` (all 737 chars) and build a small prompt:

```
ISSUE: Login crashes when the email field is empty
SIMILAR PAST FIXES: (no similar past issues)
FILE: sample_repo\auth.py
CURRENT CONTENT:
    <all 737 characters of auth.py>

Respond in EXACTLY this format:
EXPLANATION: <one sentence on why this fixes it>
```python
<the COMPLETE corrected file content>
```
Rules: keep the existing style, change as little as possible.
```

**🤖 AI CALL #2.** It replies:

````
EXPLANATION: Added a validation check for an empty or missing email before parsing it.
```python
"""Authentication logic for the demo app."""


def login(email: str, password: str):
    """Log a user in."""
    if not email or "@" not in email:
        return {"status": "invalid_email", "message": "Email is required."}

    domain = email.split("@")[1]
    ...
```
````

We split that reply in two: the `EXPLANATION:` line, and the code between the
` ``` ` fences.

```
NOTEBOOK
+ fixed_code:  "<the full corrected auth.py>"
+ explanation: "Added a validation check for an empty or missing email..."
+ attempts:    1
```

**Two things to notice:**

1. **We send the whole file, not the chunks.** We are asking for the *complete
   corrected file*. Giving the model 4 disconnected fragments and demanding a whole
   file back would make it invent the parts it cannot see. So: **chunks answer
   "which file?", the full read answers "what's in it?"**
2. **We ask for a code fence, not JSON.** An earlier version asked for structured
   JSON and it broke — a Python file inside a JSON string needs every quote and
   newline escaped, and the file's opening `"""` docstring destroyed the JSON.
   Plain text in a code fence needs no escaping. *Structured output is great for
   small fields, fragile for big code blobs.*

---

### STEP 6 — `review` — a second opinion

**🤖 AI CALL #3**, completely fresh — it has no memory of writing the fix. It sees
only three things:

```
ISSUE: Login crashes when the email field is empty
PROPOSED FILE CONTENT: <the fixed code>
AUTHOR'S EXPLANATION: Added a validation check...
```

and answers `approved` or `rejected` (plus notes).

```
NOTEBOOK
+ approved:     true
+ review_notes: "Correctly guards the empty email case."
```

This is the **generator–critic** pattern: one AI produces, another critiques. Two
cheap passes beat one careful pass.

---

### STEP 7 — the decision — ship it, or try again?

```python
if approved:                 → go to save_memory
elif attempts >= 2:          → give up looping, ship the best attempt
else:                        → go BACK to write_fix
```

**If rejected**, we return to Step 5 with one extra line injected into the prompt:

> *"A previous attempt was REJECTED. Fix this: the guard doesn't handle `None`."*

`attempts` becomes 2. At 2 we stop, no matter what.

```
         write_fix  ◄───────┐
             │              │  retry (max 2)
             ▼              │
          review  ──────────┘
             │ approved
             ▼
        save_memory
```

> **⭐ This backwards arrow is the entire reason this project uses LangGraph.**
> A normal pipeline only goes forward — it cannot say "that was wrong, do it again."
> And because a loop could run forever and burn money, the `attempts` counter gives
> it a hard ceiling. **Self-correction with a bounded cost.**

---

### STEP 8a — `save_memory` — write it in the diary

```
DIARY  (.memorydb/)
  "Login crashes when the email field is empty"
      → "Added a validation check for an empty or missing email before parsing it."
```

Saved under the stable id `issue-42`, so re-solving the same issue **overwrites**
instead of creating a duplicate. Next time a similar issue arrives, Step 3 finds this.

---

### STEP 8b — `open_pr` — raise the pull request

Calls the `open_pull_request` tool with the title, the explanation, the file path,
and the new content.

**In mock mode** (today's default) it writes a readable patch file:

```
.mock_prs/PR__sample_repo_auth.py.md
```

```markdown
# Fix: Login crashes when the email field is empty

Added a validation check for an empty or missing email before parsing it.

## Proposed content for `sample_repo\auth.py`

```python
<the complete corrected file>
```
```

**In real mode** this is where it would talk to GitHub: create a branch, commit the
new file content, and open a PR.

> ⚠️ **Real PR creation is not implemented yet** — see *Known gaps* below.

```
NOTEBOOK
+ pr_result: "[mock] Pull request saved to .mock_prs\PR__sample_repo_auth.py.md"
```

---

## 5. The whole run on one page

```
 issue #42  (a ~300-character bug report)
     │
     │  STEP 1  fetch_issue      ── tool ──► mock_data/issues.json (or GitHub API)
     ▼
     │  STEP 2  understand       ── 🤖 AI #1 ──► summary + is_bug + keywords
     ▼
     │  STEP 3  recall_memory    ── search ──► .memorydb/   (past fixes)
     ▼
     │  STEP 4  retrieve_code    ── search ──► .vectordb/   4 chunks ranked
     │                                          chunk #1's file ⇒ target_file
     ▼
     │  STEP 5  write_fix        ── read whole auth.py ──► 🤖 AI #2 ──► fixed file
     ▼
     │  STEP 6  review           ── 🤖 AI #3 ──► approved? ──┐
     │                                                 │ no  │
     │                                                 └─────┘ back to STEP 5 (max 2×)
     ▼ yes
     │  STEP 8a save_memory      ──► .memorydb/
     ▼
     │  STEP 8b open_pr          ──► .mock_prs/PR__sample_repo_auth.py.md
     ▼
   DONE
```

**Three AI calls. Roughly 1,500 tokens.** Not one of them ever saw more than one file.

---

## 6. The same flow, seen from the web API

`app/main.py` wraps all of the above in HTTP.

**Option A — wait for the answer (simple, ~20 seconds):**
```
POST /solve  {"issue_number": 42}
     → 200  {"summary": "...", "fixed_code": "...", "approved": true, ...}
```

**Option B — get a ticket, come back later (better for real UIs):**
```
POST /solve/async  {"issue_number": 42}
     → 200  {"job_id": "8f3a...", "status": "queued"}

GET  /jobs/8f3a...
     → {"status": "running"}          ... poll again ...
     → {"status": "done", "result": {...}}
```

Holding an HTTP connection open for 20 seconds is poor design (timeouts, bad UX), so
the standard pattern is: accept the work, hand back an id, let the client poll.

**Also:** the server loads the AI client and the 90 MB embedding model **before** it
accepts any traffic (in `lifespan`), so the first real user doesn't pay that cost.

---

## 7. Where the money and time go

| Where the cost is controlled | The actual setting | Effect |
|---|---|---|
| Chunk size | `chunk_size=700` | a match returns ~175 tokens, not a whole file |
| How many chunks | `RAG_TOP_K=4` | the main dial — turn it down, pay less |
| File reads | truncated at 4000 chars | tool output re-enters the prompt and costs money |
| Reply length | `max_tokens=1024` | caps what the AI writes back |
| The retry loop | `MAX_ATTEMPTS=2` | a hard ceiling on total spend per issue |
| The notebook | small fields, **no chat transcript** | prompts never grow as the run proceeds |
| Reused clients | `@lru_cache` on the model + DB handle | no reconnecting on every call |

**The one people miss is the notebook.** Most naive agents append every step to a
growing message list, so by step 8 you are re-sending everything from step 1 — the
cost grows quadratically. Our notebook has **no `messages` field at all**. Each step
builds a small fresh prompt from only the fields it needs. `review`, for example,
never sees the issue body, the retrieved chunks, or the original file.

---

## 8. Mock mode vs real mode

Set by `GITHUB_MODE` in `.env`.

| | **mock** (default) | **real** |
|---|---|---|
| Read an issue | `mock_data/issues.json` | GitHub REST API ✅ |
| Read code | local `sample_repo/` | needs a clone step ⚠️ not built |
| Open a PR | writes `.mock_prs/*.md` | ⚠️ not implemented |
| Needs a token | no | yes (`GITHUB_TOKEN`) |
| Cost / risk | zero | real API calls, real repo |

**Why mock was built first:** you can develop and test the *entire* pipeline with no
network calls, no token, and zero risk of writing to a real repository. All external
I/O is isolated behind one file (`app/tools/github_tools.py`), so switching to real
mode changes only that file.

---

## 9. Known gaps (be honest about these)

- **Real PR creation is a stub.** `open_pull_request` in real mode returns a message
  saying it isn't enabled. Reading a real issue works; opening a real PR does not.
- **`relevant_code` is stored but never used in any prompt.** The retrieved chunks
  serve only to pick `target_file`. That is a defensible design, but the field is
  currently dead weight — the natural place to use it is the `review` step, which
  today cannot see the surrounding codebase.
- **`target_file` trusts a single top result.** One unlucky chunk decides the run.
  Safer: **vote across all 4** — `auth.py` appears twice here, so it would win.
- **The 4000-character truncation is dangerous on real files.** We show the model a
  truncated file but ask for the *complete* corrected file — on a long file it would
  silently return a shortened one. Safe today only because `auth.py` is 23 lines.
- **Nothing checks the generated code is valid Python.** An `ast.parse()` check before
  the review step would be a free, instant rejection with no tokens spent.
- **Re-indexing while the server runs breaks search** — the retriever caches a handle
  to a folder that `build_index()` deletes and recreates.
- **MCP is built and demoed but not on the main path** — the graph calls the tools
  directly, in-process.

---

## 10. Run it yourself

```powershell
# one-time setup
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # then paste your free GROQ_API_KEY into it

# the whole flow, end to end
python -m scripts.phase8_demo

# or as a web service
uvicorn app.main:app --reload
#   → open http://127.0.0.1:8000/docs and try POST /solve with {"issue_number": 42}
```

**Expected:** the node names print in order, `approved=True`, and a patch file appears
in `.mock_prs/`.

---

## 11. Interview questions you can now answer

**Q: Walk me through your system.**
An issue number comes in over FastAPI. A LangGraph state machine fetches the issue,
compresses it to a summary plus keywords, recalls similar past fixes from a long-term
vector memory, runs a semantic search over a chunked index of the codebase to identify
the target file, reads that one file, writes a corrected version, and passes it to a
reviewer node that can send it back for a rewrite — bounded at two attempts. On
approval it saves the solution to memory and opens a pull request.

**Q: How do you avoid blowing the context window?**
I never send the codebase. I chunk and embed it once, then retrieve only the top 4
chunks per query and use their file metadata to pick a single file to read. The graph
state holds small structured fields instead of a growing chat transcript, so prompts
don't compound. Tool output is truncated, replies are capped at 1024 tokens, and the
retry loop is capped at 2.

**Q: Why LangGraph and not a plain chain?**
Because I need an arrow that points backwards. The reviewer can reject a fix and send
it back to the writer with notes. A chain is linear and cannot express a cycle.

**Q: How do you stop it from looping forever?**
A retry counter in the state, checked by the router. At `MAX_ATTEMPTS` it exits with
the best attempt rather than looping.

**Q: How does it know which file to fix?**
Every chunk in the vector store carries its source file path as metadata. The
top-ranked chunk's path becomes the target file — so retrieval does double duty as
code localization, and I get it for free from the same search.

**Q: Why local embeddings but a cloud LLM?**
Groq has no embedding model, and embeddings are cheap and repetitive — running them
locally is free and keeps the code on my machine. Reasoning is the expensive part and
benefits most from a fast hosted model. Local embeddings + cloud reasoning.

---

✅ **You understand this doc when you can draw the diagram in section 5 from memory and
explain why the arrow from `review` back to `write_fix` exists.**
