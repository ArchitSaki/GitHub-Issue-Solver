"""
state.py — the shared "notebook" that flows through the whole graph.

Every node receives this State, reads what it needs, and returns ONLY the keys it
changed. LangGraph merges those updates for us.

DESIGN NOTE (token efficiency — one of our core rules):
    Notice we do NOT keep a giant chat transcript in the State. We keep small,
    structured fields (a summary, a few code chunks, a plan). Each node builds a
    tiny focused prompt from just the fields it needs, instead of resending an
    ever-growing conversation. That is "optimal context window use" in practice.
"""

from typing import TypedDict


class SolverState(TypedDict, total=False):
    # --- input ---
    issue_number: int          # which issue to solve

    # --- filled by fetch_issue ---
    issue_text: str            # raw issue (title + labels + body)

    # --- filled by understand ---
    summary: str               # one-line problem statement
    is_bug: bool               # bug vs feature request
    keywords: list[str]        # search terms for RAG

    # --- filled by recall_memory ---
    past_experience: str       # similar past issues + how we fixed them

    # --- filled by retrieve_code ---
    relevant_code: str         # the few RAG chunks that matter
    target_file: str           # the file we decided to change

    # --- filled by write_fix ---
    fixed_code: str            # the FULL corrected content of target_file
    explanation: str           # why this fixes it

    # --- filled by review ---
    approved: bool             # did the reviewer accept the fix?
    review_notes: str          # what to improve if rejected
    attempts: int              # retry counter -> stops infinite loops

    # --- filled by open_pr ---
    pr_result: str             # where the PR/patch ended up
