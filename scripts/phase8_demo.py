"""
phase8_demo.py — THE FULL SYSTEM, end to end. Run with:

    python -m scripts.phase8_demo

Issue #42 goes in -> a real code fix comes out (saved as a mock PR).
Every phase you built is used exactly once here.
"""

from app.rag.indexer import build_index
from app.graph.builder import build_solver_graph


if __name__ == "__main__":
    # Make sure the code index exists (Phase 5). Cheap for our tiny sample repo.
    build_index("sample_repo")

    graph = build_solver_graph()

    print("\n=========== SOLVING ISSUE #42 ===========\n")
    final = graph.invoke({"issue_number": 42})

    print("\n=========== RESULT ===========")
    print("SUMMARY     :", final["summary"])
    print("IS BUG      :", final["is_bug"])
    print("TARGET FILE :", final["target_file"])
    print("ATTEMPTS    :", final["attempts"])
    print("APPROVED    :", final["approved"])
    print("EXPLANATION :", final["explanation"])
    print("PR          :", final["pr_result"])

    print("\n--- THE FIXED CODE ---")
    print(final["fixed_code"])
    print("\n[DONE] Phase 8: full agentic pipeline ran end to end.")
