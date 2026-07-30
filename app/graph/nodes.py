"""
nodes.py — the workers of our graph. One small function per step.

Each node: reads State -> does ONE job -> returns a dict of changed keys.

Where each phase shows up:
    fetch_issue   -> Phase 7 tools
    understand    -> Phase 2 structured output
    recall_memory -> Phase 6 long-term memory
    retrieve_code -> Phase 5 RAG
    write_fix     -> Phase 2 LLM + retrieved context
    review        -> a second LLM pass (self-check) -> enables the retry LOOP
    save_memory   -> Phase 6 (write side)
    open_pr       -> Phase 7 tools
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.agents.llm import get_llm
from app.memory.store import get_memory
from app.rag.retriever import search_code, format_context
from app.tools.github_tools import get_issue, read_repo_file, open_pull_request
from app.graph.state import SolverState

MAX_ATTEMPTS = 2   # cap retries so a stubborn model can't loop forever (cost control)


# --- structured shapes we ask the LLM to fill (Phase 2 technique) ------------
#
# WHY STRING ENUMS INSTEAD OF bool?
#   We first used `is_bug: bool`. Groq rejected the call with:
#       `/is_bug`: expected boolean, but got string   (model sent "false", not false)
#   Weaker/open models frequently STRINGIFY booleans. A Literal string enum is far
#   more robust: "bug"/"feature" is a token the model produces naturally, and we
#   convert it to a real bool ourselves. Design the schema for the model you have.
class Understanding(BaseModel):
    summary: str = Field(description="one sentence describing the problem")
    issue_type: Literal["bug", "feature"] = Field(
        description="'bug' if something is broken, 'feature' if it is a new request"
    )
    keywords: list[str] = Field(description="2-4 keywords to search the codebase")


class Review(BaseModel):
    verdict: Literal["approved", "rejected"] = Field(
        description="'approved' if the fix is correct and complete, else 'rejected'"
    )
    notes: str = Field(description="if rejected, what must be improved")


# ---------------------------------------------------------------------------
# NODE 1: fetch the issue (uses our Phase 7 tool)
# ---------------------------------------------------------------------------
def fetch_issue(state: SolverState) -> dict:
    print("[node] fetch_issue")
    text = get_issue.invoke({"issue_number": state["issue_number"]})
    return {"issue_text": text, "attempts": 0}


# ---------------------------------------------------------------------------
# NODE 2: understand it (cheap, small prompt -> structured data)
# ---------------------------------------------------------------------------
def _invoke_with_retry(structured_llm, prompt: str, attempts: int = 3):
    """Call a structured-output LLM, retrying on malformed output.

    WHY: weaker models occasionally emit invalid tool-call JSON (wrong type, bad
    escaping). These failures are STOCHASTIC — the same prompt usually succeeds on
    a retry. A tiny retry wrapper turns a flaky pipeline into a reliable one.
    This is standard practice when building on top of LLMs.
    """
    last_error = None
    for i in range(attempts):
        try:
            return structured_llm.invoke(prompt)
        except Exception as exc:               # noqa: BLE001 - provider-specific errors
            last_error = exc
            print(f"       [retry {i + 1}/{attempts}] structured output failed")
    raise last_error


def understand(state: SolverState) -> dict:
    print("[node] understand")
    llm = get_llm().with_structured_output(Understanding)
    u = _invoke_with_retry(
        llm,
        "Summarize this GitHub issue into the required structure.\n\n"
        + state["issue_text"],
    )
    # Convert the model-friendly string enum into a real boolean for our State.
    return {
        "summary": u.summary,
        "is_bug": u.issue_type == "bug",
        "keywords": u.keywords,
    }


# ---------------------------------------------------------------------------
# NODE 3: recall similar past issues (Phase 6 memory)
# ---------------------------------------------------------------------------
def recall_memory(state: SolverState) -> dict:
    print("[node] recall_memory")
    hits = get_memory().recall(state["summary"])
    if not hits:
        return {"past_experience": "(no similar past issues)"}

    lines = [f"- Past issue: {h['past_issue']}\n  Fix: {h['past_solution']}" for h in hits]
    return {"past_experience": "\n".join(lines)}


# ---------------------------------------------------------------------------
# NODE 4: retrieve only the relevant code (Phase 5 RAG)
# ---------------------------------------------------------------------------
def retrieve_code(state: SolverState) -> dict:
    print("[node] retrieve_code")
    # Search using the summary + keywords -> better recall than the raw issue text.
    query = state["summary"] + " " + " ".join(state.get("keywords", []))
    chunks = search_code(query)

    # The top-ranked chunk's file is our best guess at the file to fix.
    target = chunks[0]["source"] if chunks else ""
    return {"relevant_code": format_context(chunks), "target_file": target}


# ---------------------------------------------------------------------------
# NODE 5: write the fix
#
# WHY NOT structured output here?
#   We first tried with_structured_output() to get {target_file, fixed_code, ...}.
#   It FAILED: putting a whole Python file inside a JSON string means escaping
#   quotes/newlines, and the model produced invalid JSON (a docstring """ broke it).
#
#   LESSON: structured output is great for SMALL scalar fields, but fragile for
#   large code blobs. For code, ask for a markdown code fence and extract it —
#   no escaping required. Right tool for the right job.
# ---------------------------------------------------------------------------
def _extract_code(text: str) -> str:
    """Pull the code out of a ```...``` fenced block."""
    if "```" not in text:
        return text.strip()

    block = text.split("```")[1]              # content of the first fence
    # Drop a leading language tag like "python".
    if "\n" in block:
        first_line, rest = block.split("\n", 1)
        if first_line.strip().lower() in {"python", "py", ""}:
            return rest.strip()
    return block.strip()


def _extract_explanation(text: str) -> str:
    """Read the EXPLANATION: line that comes before the code fence."""
    head = text.split("```")[0]
    for line in head.splitlines():
        if line.upper().startswith("EXPLANATION:"):
            return line.split(":", 1)[1].strip()
    return head.strip()[:300] or "Fix applied."


def write_fix(state: SolverState) -> dict:
    print("[node] write_fix")

    # Read the WHOLE target file: we must output its complete corrected content,
    # and RAG chunks alone may be partial.
    current = read_repo_file.invoke({"path": state["target_file"]})

    # If a previous review rejected us, include the notes so we improve.
    retry_note = ""
    if state.get("review_notes") and not state.get("approved", False):
        retry_note = f"\nA previous attempt was REJECTED. Fix this: {state['review_notes']}\n"

    llm = get_llm()   # plain text call - no JSON schema to break
    response = llm.invoke(
        "You are fixing a bug in a Python file.\n"
        f"\nISSUE: {state['summary']}\n"
        f"\nSIMILAR PAST FIXES (for guidance):\n{state.get('past_experience', '')}\n"
        f"\nFILE: {state['target_file']}\n"
        f"\nCURRENT CONTENT:\n{current}\n"
        f"{retry_note}"
        "\nRespond in EXACTLY this format and nothing else:\n"
        "EXPLANATION: <one sentence on why this fixes it>\n"
        "```python\n"
        "<the COMPLETE corrected file content>\n"
        "```\n"
        "Rules: keep the existing style, change as little as possible."
    ).content

    return {
        "fixed_code": _extract_code(response),
        "explanation": _extract_explanation(response),
        "attempts": state.get("attempts", 0) + 1,
    }


# ---------------------------------------------------------------------------
# NODE 6: review the fix (a second opinion -> drives the retry loop)
# ---------------------------------------------------------------------------
def review(state: SolverState) -> dict:
    print("[node] review")
    llm = get_llm().with_structured_output(Review)
    r = _invoke_with_retry(
        llm,
        "Review this proposed fix. Approve only if it truly resolves the issue "
        "and the code is valid.\n"
        f"\nISSUE: {state['summary']}\n"
        f"\nPROPOSED FILE CONTENT:\n{state['fixed_code']}\n"
        f"\nAUTHOR'S EXPLANATION: {state['explanation']}",
    )
    approved = r.verdict == "approved"
    print(f"       -> approved={approved}")
    return {"approved": approved, "review_notes": r.notes}


# ---------------------------------------------------------------------------
# NODE 7: remember what we did (Phase 6 memory, write side)
# ---------------------------------------------------------------------------
def save_memory(state: SolverState) -> dict:
    print("[node] save_memory")
    get_memory().remember(
        issue_summary=state["summary"],
        solution=state["explanation"],
        memory_id=f"issue-{state['issue_number']}",
    )
    return {}


# ---------------------------------------------------------------------------
# NODE 8: open the pull request (Phase 7 tool)
# ---------------------------------------------------------------------------
def open_pr(state: SolverState) -> dict:
    print("[node] open_pr")
    result = open_pull_request.invoke({
        "title": f"Fix: {state['summary']}",
        "body": state["explanation"],
        "file_path": state["target_file"],
        "new_content": state["fixed_code"],
    })
    return {"pr_result": result}


# ---------------------------------------------------------------------------
# THE ROUTER: after review, do we retry or ship it?
# ---------------------------------------------------------------------------
def route_after_review(state: SolverState) -> str:
    """Conditional edge: 'approved' -> finish, 'retry' -> write_fix again.

    The attempts cap is what makes the loop SAFE (bounded cost).
    """
    if state.get("approved"):
        return "approved"
    if state.get("attempts", 0) >= MAX_ATTEMPTS:
        print(f"       -> not approved, but hit {MAX_ATTEMPTS} attempts. Shipping anyway.")
        return "approved"
    print("       -> rejected, retrying the fix")
    return "retry"
