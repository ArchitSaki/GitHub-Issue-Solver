# fastapi.md — Phase 9: The Backend API

> Our agent becomes a real web service. This is what makes it a *product*, not a script.

Files: `app/main.py`, `app/models.py`.

---

## 1. Run it

```powershell
uvicorn app.main:app --reload
```
Then open **http://127.0.0.1:8000/docs** — FastAPI generates interactive Swagger docs
from our Pydantic models automatically. (Screenshot this for your portfolio.)

## 2. The endpoints

| Method | Path | What it does |
|--------|------|--------------|
| GET | `/health` | liveness check (for load balancers/monitoring) |
| POST | `/index` | (re)build the RAG code index |
| POST | `/solve` | solve an issue and WAIT (~20s) for the result |
| POST | `/solve/async` | queue a solve, return a `job_id` immediately |
| GET | `/jobs/{job_id}` | poll a background job's status/result |

Example:
```powershell
curl -X POST http://127.0.0.1:8000/solve -H "Content-Type: application/json" -d "{\"issue_number\": 42}"
```

## 3. THE key design decision: sync vs async endpoints

An agent run takes ~20 seconds. Holding an HTTP connection open that long is bad design
(proxy timeouts, retries, terrible UX, wasted connections).

**The standard pattern** (used by every real async AI API):
```
POST /solve/async   ->  202-style response: {"job_id": "..."}   (instant)
GET  /jobs/{id}     ->  {"status": "running"}  ... then {"status":"done", "result": {...}}
```
We keep `/solve` (blocking) too — it's convenient for testing and demos.

> Interview line: *"Long-running agent work goes through a job queue with polling, so the
> HTTP layer stays fast and clients aren't holding 20-second connections."*

## 4. THE key correctness trap: blocking the event loop

FastAPI is **async**. Our graph nodes are ordinary **sync** functions that block on
network calls. If you call blocking code directly inside `async def`, you block the whole
event loop and **every other request freezes**.

Our fix in `/solve`:
```python
final_state = await GRAPH.ainvoke({...})   # runs sync nodes in a thread pool
```
`ainvoke` (LangGraph's async entry point) offloads sync work to threads, so the event loop
stays free.

> Interview line: *"Blocking calls inside an async endpoint stall the event loop; I use the
> async graph API so sync nodes run in a thread pool."*

## 5. Warm-up at startup (latency)

The first LLM/embedding call is slow — clients connect, the embedding model loads from
disk. We do that in `lifespan` **before** the server accepts traffic:
```python
@asynccontextmanager
async def lifespan(app):
    GRAPH = build_solver_graph()
    get_embeddings().embed_query("warm up")   # load the model NOW
    get_llm()
    yield
```
So the *first user* doesn't pay the cold-start cost. Directly serves our low-latency rule.

## 6. Why Pydantic models (`app/models.py`)

One class definition gives us three things free:
1. **Validation** — bad input returns a clean `422`, never a crash inside the agent.
2. **Documentation** — the Swagger UI is generated from them.
3. **Serialization** — consistent JSON responses.

## 7. A REAL bug we hit: the model stringified a boolean

`/solve/async` for issue #43 failed with:
```
`/is_bug`: expected boolean, but got string
failed_generation: {"is_bug": "false", ...}
```
- **Root cause:** the model returned the *string* `"false"` instead of the *boolean* `false`.
  Groq validates the tool-call schema server-side and rejected it. Weaker/open models
  frequently stringify booleans.
- **Fix (two parts):**
  1. Replaced `bool` fields with `Literal["bug","feature"]` / `Literal["approved","rejected"]`
     string enums, converting to a real bool in our code.
  2. Added `_invoke_with_retry()` — these failures are **stochastic**, so a retry usually
     succeeds.
- **Lesson:** *design the schema for the model you actually have.* String enums are more
  robust than booleans for smaller models, and always wrap LLM calls in retries.

## 8. Production notes (say these to show maturity)

Our `JOBS` dict is in-memory — fine for a demo, but:
- jobs are lost on restart, and don't work across multiple server processes,
- **production:** use Redis or a database, plus a real worker queue (Celery/RQ/arq).

Other next steps: authentication (API keys), rate limiting, structured logging,
request tracing, and streaming partial results over SSE/WebSocket.

## 9. Interview questions you can now answer

- **Q: Why FastAPI?** Async-native (good for I/O-bound LLM calls), automatic validation
  and OpenAPI docs from Pydantic, and it's the standard for Python ML/AI services.
- **Q: How do you handle a 20-second agent run in an API?** Background job + polling
  (`/solve/async` → `/jobs/{id}`), so requests return instantly.
- **Q: What happens if you call blocking code in an async endpoint?** It blocks the event
  loop and stalls all concurrent requests; use async APIs or a thread pool.
- **Q: How do you reduce cold-start latency?** Warm the models and build the graph in the
  startup lifespan, before serving traffic.
- **Q: How would you scale this?** External job store (Redis) + worker processes, multiple
  uvicorn workers, caching, and a managed vector DB.

✅ Phase 9 done when `/health`, `/solve`, and `/solve/async` + `/jobs/{id}` all work.
