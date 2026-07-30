"""
main.py — the FastAPI backend: our agent exposed as a real web service.

RUN IT:
    uvicorn app.main:app --reload
    then open http://127.0.0.1:8000/docs  (interactive Swagger UI, auto-generated)

ENDPOINTS:
    GET  /health          -> is the service alive?
    POST /index           -> (re)build the RAG code index
    POST /solve           -> solve an issue and WAIT for the answer (~20s)
    POST /solve/async     -> queue a solve, return a job_id immediately
    GET  /jobs/{job_id}   -> poll for the background job's result

TWO IMPORTANT DESIGN DECISIONS (both are interview gold):

 1. WARM-UP AT STARTUP (latency).
    The first call to an LLM/embedding model is slow (clients connect, the embedding
    model loads from disk). If we did that during the first user request, that user
    waits. Instead we warm everything in `lifespan`, BEFORE serving traffic.

 2. BLOCKING WORK IN AN ASYNC SERVER (correctness).
    Our graph nodes are normal SYNC functions that block on network calls. If we
    called them directly inside an `async def` endpoint, they would block the event
    loop and freeze the WHOLE server for every user. We avoid that by using
    `await graph.ainvoke(...)`, which runs sync nodes in a thread pool.
"""

import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException

from app.agents.llm import get_embeddings, get_llm
from app.graph.builder import build_solver_graph
from app.models import JobCreated, JobStatus, SolveRequest, SolveResponse
from app.rag.indexer import build_index

# Built once at startup and reused for every request (see lifespan below).
GRAPH = None

# A very simple in-memory job store: job_id -> JobStatus.
# NOTE: fine for a demo. In production you'd use Redis or a database so jobs
# survive a restart and work across multiple server processes.
JOBS: dict[str, JobStatus] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs ONCE before the server accepts traffic, and again on shutdown.

    This is our warm-up: build the graph and load the embedding model now, so the
    first real user doesn't pay that cost.
    """
    global GRAPH
    print("[startup] building graph...")
    GRAPH = build_solver_graph()

    print("[startup] warming the embedding model...")
    get_embeddings().embed_query("warm up")   # forces the model to load
    get_llm()                                  # builds + caches the LLM client

    print("[startup] ready.")
    yield                                      # <-- the app serves requests here
    print("[shutdown] bye.")


app = FastAPI(
    title="Agentic GitHub Issue Solver",
    description="Give it a GitHub issue number; it reads the code, writes a fix, "
                "reviews it, and opens a pull request.",
    version="1.0.0",
    lifespan=lifespan,
)


def _to_response(issue_number: int, state: dict) -> SolveResponse:
    """Turn the graph's final State into our API response shape."""
    return SolveResponse(
        issue_number=issue_number,
        summary=state.get("summary", ""),
        is_bug=state.get("is_bug", False),
        target_file=state.get("target_file", ""),
        explanation=state.get("explanation", ""),
        fixed_code=state.get("fixed_code", ""),
        approved=state.get("approved", False),
        attempts=state.get("attempts", 0),
        pr_result=state.get("pr_result", ""),
    )


@app.get("/health")
async def health():
    """Cheap liveness check — used by load balancers and uptime monitors."""
    return {"status": "ok", "graph_ready": GRAPH is not None}


@app.post("/index")
async def index_repo(repo_dir: str = "sample_repo"):
    """(Re)build the RAG index. Run this whenever the codebase changes."""
    chunks = build_index(repo_dir)
    return {"status": "ok", "chunks_indexed": chunks}


@app.post("/solve", response_model=SolveResponse)
async def solve(request: SolveRequest):
    """Solve an issue and WAIT for the result (~20s).

    Simple to call, but the client is blocked while it runs. Good for testing;
    for real UIs prefer /solve/async below.
    """
    try:
        # ainvoke() runs our sync nodes in a thread pool, so the event loop
        # stays free to serve other requests.
        final_state = await GRAPH.ainvoke({"issue_number": request.issue_number})
        return _to_response(request.issue_number, final_state)
    except Exception as exc:
        # Never leak a raw traceback to the client; log it, return a clean error.
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Solve failed: {exc}")


def _run_job(job_id: str, issue_number: int) -> None:
    """The actual work for a background job (runs in a worker thread)."""
    JOBS[job_id].status = "running"
    try:
        final_state = GRAPH.invoke({"issue_number": issue_number})
        JOBS[job_id].result = _to_response(issue_number, final_state)
        JOBS[job_id].status = "done"
    except Exception as exc:
        traceback.print_exc()
        JOBS[job_id].error = str(exc)
        JOBS[job_id].status = "error"


@app.post("/solve/async", response_model=JobCreated)
async def solve_async(request: SolveRequest, background_tasks: BackgroundTasks):
    """Queue a solve and return IMMEDIATELY with a job_id.

    WHY: an agent run takes ~20s. Holding an HTTP connection open that long is poor
    design (timeouts, bad UX). Standard pattern: accept the work, return an id, let
    the client poll. This is how real async AI APIs behave.
    """
    job_id = str(uuid.uuid4())
    JOBS[job_id] = JobStatus(job_id=job_id, status="queued")
    background_tasks.add_task(_run_job, job_id, request.issue_number)
    return JobCreated(job_id=job_id)


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    """Poll the status/result of a background solve."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
