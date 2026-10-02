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

MAX_ATTEMPTS_BUG = 2      # bug fixes: 2 attempts is usually enough
MAX_ATTEMPTS_FEATURE = 3  # features: allow one extra attempt (more creative, needs more room)


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
        description="'approved' if the change correctly addresses the issue, else 'rejected'"
    )
    notes: str = Field(description="if rejected, what specifically must be improved")


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
    # Drop a leading language tag like "python", "html", "javascript", etc.
    if "\n" in block:
        first_line, rest = block.split("\n", 1)
        tag = first_line.strip().lower()
        if tag in {"python", "py", "html", "javascript", "js", "css", "json", "typescript", "ts", ""}:
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

    is_bug = state.get("is_bug", True)

    # Read the WHOLE target file: we must output its complete corrected content,
    # and RAG chunks alone may be partial.
    current = read_repo_file.invoke({"path": state["target_file"]})

    # If a previous review rejected us, include the notes so we improve.
    retry_note = ""
    if state.get("review_notes") and not state.get("approved", False):
        retry_note = f"\nA previous attempt was REJECTED. Improve it: {state['review_notes']}\n"

    # --- Bug fix prompt: minimal, targeted, preserve existing behaviour ------
    if is_bug:
        prompt = (
            "You are a senior engineer fixing a bug in a codebase.\n"
            f"\nBUG: {state['summary']}\n"
            f"\nSIMILAR PAST FIXES (for guidance):\n{state.get('past_experience', '')}\n"
            f"\nFILE TO FIX: {state['target_file']}\n"
            f"\nCURRENT CONTENT:\n{current}\n"
            f"{retry_note}"
            "\nRespond in EXACTLY this format and nothing else:\n"
            "EXPLANATION: <one sentence explaining the root cause and the fix>\n"
            "```\n"
            "<the COMPLETE corrected file content — do NOT omit any unchanged part>\n"
            "```\n"
            "Rules: change as LITTLE as possible, keep the existing style."
        )
    # --- Feature request prompt: creative, additive, explain tradeoffs -------
    else:
        prompt = (
            "You are a senior engineer implementing a feature request in a codebase.\n"
            f"\nFEATURE REQUEST: {state['summary']}\n"
            f"\nRELEVANT EXISTING CODE (context from RAG):\n{state.get('relevant_code', '')}\n"
            f"\nSIMILAR PAST WORK (for guidance):\n{state.get('past_experience', '')}\n"
            f"\nFILE TO MODIFY: {state['target_file']}\n"
            f"\nCURRENT CONTENT:\n{current}\n"
            f"{retry_note}"
            "\nInstructions:\n"
            "- Implement the feature request as faithfully as possible given the existing file.\n"
            "- If the request requires changes beyond this single file (e.g. a full framework\n"
            "  migration like plain HTML -> React), implement the best possible improvement\n"
            "  WITHIN the current file's language/format and note the limitation in EXPLANATION.\n"
            "- Do NOT omit any unchanged part of the file.\n"
            "\nRespond in EXACTLY this format and nothing else:\n"
            "EXPLANATION: <one sentence on what was added/changed and any limitations>\n"
            "```\n"
            "<the COMPLETE updated file content>\n"
            "```"
        )

    llm = get_llm()   # plain text call - no JSON schema to break
    response = llm.invoke(prompt).content

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
    is_bug = state.get("is_bug", True)
    llm = get_llm().with_structured_output(Review)

    if is_bug:
        # Bug review: strict — the code must actually fix the defect.
        review_prompt = (
            "You are a code reviewer. Approve ONLY if the proposed change genuinely fixes "
            "the reported bug and the code is syntactically valid.\n"
            f"\nBUG: {state['summary']}\n"
            f"\nPROPOSED FILE CONTENT:\n{state['fixed_code']}\n"
            f"\nAUTHOR'S EXPLANATION: {state['explanation']}\n"
            "\nApprove if the bug is addressed. Reject if the bug is not fixed or the code is broken."
        )
    else:
        # Feature review: lenient — the change must add value towards the request.
        # We do NOT reject just because the feature can't be fully implemented in one file.
        review_prompt = (
            "You are a code reviewer evaluating a feature request implementation.\n"
            f"\nFEATURE REQUEST: {state['summary']}\n"
            f"\nPROPOSED FILE CONTENT:\n{state['fixed_code']}\n"
            f"\nAUTHOR'S EXPLANATION: {state['explanation']}\n"
            "\nApprove if:\n"
            "  - The change meaningfully moves towards the requested feature, OR\n"
            "  - The author explains a valid limitation (e.g. framework migration needs more files).\n"
            "Reject ONLY if the file content is unchanged, broken, or completely unrelated."
        )

    r = _invoke_with_retry(llm, review_prompt)
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
    # Use "Feat:" prefix for feature requests, "Fix:" for bugs.
    # This follows the conventional commits standard (interviewers love this detail).
    pr_prefix = "Fix" if state.get("is_bug", True) else "Feat"
    result = open_pull_request.invoke({
        "title": f"{pr_prefix}: {state['summary']}",
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
    Bugs get 2 attempts (tight, targeted). Features get 3 (more creative room).
    """
    if state.get("approved"):
        return "approved"
    max_attempts = MAX_ATTEMPTS_BUG if state.get("is_bug", True) else MAX_ATTEMPTS_FEATURE
    if state.get("attempts", 0) >= max_attempts:
        print(f"       -> not approved, but hit {max_attempts} attempts. Shipping anyway.")
        return "approved"
    print("       -> rejected, retrying the fix")
    return "retry"
