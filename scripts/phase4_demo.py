"""
phase4_demo.py — your first LangGraph. Run with:

    python -m scripts.phase4_demo

WHAT YOU'LL LEARN (the 3 pieces of every LangGraph):
    1. STATE  -> a shared "notebook" that flows through the whole graph
    2. NODES  -> small functions that read the state and return updates to it
    3. EDGES  -> the wiring between nodes (including CONDITIONAL edges = branching)

This mini graph is a TINY version of our real project:
    understand the issue  ->  (is it a bug or a feature?)  ->  write the right plan

In Phase 8 we grow this exact shape into the full GitHub solver.
"""

from typing import TypedDict, Literal

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from app.agents.llm import get_llm


# --- 1) STATE: the shared notebook -----------------------------------------
# Every node receives this and can update parts of it. Think of it as the
# "memory of the current run". We use a TypedDict so the keys are clear.
class IssueState(TypedDict):
    issue_text: str        # INPUT: the raw issue
    summary: str           # filled by the 'understand' node
    is_bug: bool           # filled by 'understand' -> used to choose the branch
    keywords: list[str]    # filled by 'understand'
    plan: str              # OUTPUT: filled by a 'plan' node


# The exact shape we want the LLM to return (from Phase 2 — structured output).
class Understanding(BaseModel):
    summary: str = Field(description="one-sentence summary of the issue")
    is_bug: bool = Field(description="true if a bug, false if a feature request")
    keywords: list[str] = Field(description="2-4 code-search keywords")


# --- 2) NODES: functions that read state and return an UPDATE ---------------
# KEY RULE: a node returns a dict of ONLY the keys it wants to change.
# LangGraph merges that into the state for you. You never mutate state directly.

def understand(state: IssueState) -> dict:
    print("[node] understand: reading the issue...")
    llm = get_llm().with_structured_output(Understanding)
    u = llm.invoke(
        "Summarize this GitHub issue into the required structure:\n\n"
        + state["issue_text"]
    )
    return {"summary": u.summary, "is_bug": u.is_bug, "keywords": u.keywords}


def write_bugfix_plan(state: IssueState) -> dict:
    print("[node] write_bugfix_plan: it's a BUG")
    llm = get_llm()
    plan = llm.invoke(
        "Write a short numbered 3-step plan to FIX this bug. Be concise.\n\n"
        f"Bug: {state['summary']}"
    ).content
    return {"plan": plan}


def write_feature_plan(state: IssueState) -> dict:
    print("[node] write_feature_plan: it's a FEATURE")
    llm = get_llm()
    plan = llm.invoke(
        "Write a short numbered 3-step plan to IMPLEMENT this feature. Be concise.\n\n"
        f"Feature: {state['summary']}"
    ).content
    return {"plan": plan}


# --- 3) The ROUTER: a function that picks the next node (conditional edge) ---
# It returns a STRING label; we map that label to a node when wiring the graph.
def route_by_type(state: IssueState) -> Literal["bugfix", "feature"]:
    return "bugfix" if state["is_bug"] else "feature"


# --- Build (wire) the graph -------------------------------------------------
def build_graph():
    builder = StateGraph(IssueState)

    # register the nodes (name -> function)
    builder.add_node("understand", understand)
    builder.add_node("bugfix", write_bugfix_plan)
    builder.add_node("feature", write_feature_plan)

    # wire the edges:
    builder.add_edge(START, "understand")          # entry point
    builder.add_conditional_edges(                 # BRANCH based on router result
        "understand",
        route_by_type,
        {"bugfix": "bugfix", "feature": "feature"},
    )
    builder.add_edge("bugfix", END)                # both branches finish
    builder.add_edge("feature", END)

    return builder.compile()   # .compile() turns the blueprint into a runnable graph


if __name__ == "__main__":
    graph = build_graph()

    issue = (
        "Title: App crashes on login\n"
        "Clicking 'Login' with an empty email crashes the app with a "
        "NullPointerException instead of showing a validation message."
    )

    # .invoke() runs the graph from START to END, returning the FINAL state.
    final_state = graph.invoke({"issue_text": issue})

    print("\n--- FINAL STATE ---")
    print("summary :", final_state["summary"])
    print("is_bug  :", final_state["is_bug"])
    print("keywords:", final_state["keywords"])
    print("plan    :\n" + final_state["plan"])
    print("\n[DONE] Phase 4: you built a stateful graph that branches on its own.")
