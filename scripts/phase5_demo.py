"""
phase5_demo.py — see RAG in action. Run with:

    python -m scripts.phase5_demo

It (1) builds an index of sample_repo, then (2) asks a question and shows that RAG
retrieves ONLY the relevant file (auth.py), not the whole repo. That's the whole
point: feed the LLM a little relevant context instead of everything.
"""

from app.rag.indexer import build_index
from app.rag.retriever import search_code, format_context


if __name__ == "__main__":
    # STEP 1: build the searchable index from our sample repo.
    build_index("sample_repo")

    # STEP 2: a question that matches the login bug.
    query = "login crashes when the email field is empty"
    print(f"\nQUERY: {query}\n")

    chunks = search_code(query)   # returns top-k relevant chunks

    print(f"Retrieved {len(chunks)} chunks (out of the whole repo):\n")
    for i, c in enumerate(chunks, 1):
        first_line = c["snippet"].strip().splitlines()[0]
        print(f"  {i}. {c['source']}   ->  {first_line!r}")

    print("\nNotice: the top hit is auth.py (the buggy file), not database.py/utils.py.")
    print("That relevant context is what we'd hand to the LLM — small + focused.\n")
    print("[DONE] Phase 5: RAG retrieves only what matters.")
