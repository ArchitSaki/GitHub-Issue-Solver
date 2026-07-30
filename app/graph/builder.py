"""
builder.py — wire the nodes into the actual workflow graph.

THE SHAPE:

    START -> fetch_issue -> understand -> recall_memory -> retrieve_code
                                                              |
                                                              v
                                                          write_fix  <--+
                                                              |         |
                                                              v         | retry
                                                            review -----+
                                                              | approved
                                                              v
                                                    save_memory -> open_pr -> END

The retry edge (review -> write_fix) is the thing a plain chain CANNOT do.
That cycle is exactly why we use LangGraph.
"""

from langgraph.graph import StateGraph, START, END

from app.graph.state import SolverState
from app.graph import nodes


def build_solver_graph():
    builder = StateGraph(SolverState)

    # 1) register the nodes
    builder.add_node("fetch_issue", nodes.fetch_issue)
    builder.add_node("understand", nodes.understand)
    builder.add_node("recall_memory", nodes.recall_memory)
    builder.add_node("retrieve_code", nodes.retrieve_code)
    builder.add_node("write_fix", nodes.write_fix)
    builder.add_node("review", nodes.review)
    builder.add_node("save_memory", nodes.save_memory)
    builder.add_node("open_pr", nodes.open_pr)

    # 2) the straight-line part
    builder.add_edge(START, "fetch_issue")
    builder.add_edge("fetch_issue", "understand")
    builder.add_edge("understand", "recall_memory")
    builder.add_edge("recall_memory", "retrieve_code")
    builder.add_edge("retrieve_code", "write_fix")
    builder.add_edge("write_fix", "review")

    # 3) the DECISION: loop back to write_fix, or move on to shipping
    builder.add_conditional_edges(
        "review",
        nodes.route_after_review,
        {
            "retry": "write_fix",       # <-- the cycle
            "approved": "save_memory",
        },
    )

    # 4) finish
    builder.add_edge("save_memory", "open_pr")
    builder.add_edge("open_pr", END)

    return builder.compile()
