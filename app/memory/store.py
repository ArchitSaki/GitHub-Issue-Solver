"""
store.py — LONG-TERM memory: remember past solved issues and recall similar ones.

TWO KINDS OF MEMORY (know this cold for interviews):

  SHORT-TERM memory = the current run's context (the message list / graph State).
                      It lives only while one issue is being solved, then it's gone.
                      (We already used this in the Phase 3 agent loop.)

  LONG-TERM memory  = knowledge that survives ACROSS runs. Here: a vector store of
                      past issues + how we solved them. When a NEW issue arrives, we
                      recall similar past ones and reuse that experience.

WHY LONG-TERM MEMORY HELPS OUR GOALS:
  - Fewer tokens / lower latency: if we solved a near-identical issue before, we can
    reuse the plan instead of re-reasoning the whole thing from scratch.
  - Smarter over time: the system "learns" from what it has already done.

HOW: it's basically "RAG over our own past solutions" — same embedding + vector search
tech from Phase 5, but the documents are past issue/solution pairs, not code.
"""

from functools import lru_cache

from langchain_chroma import Chroma

from app.agents.llm import get_embeddings
from app.config import settings


class LongTermMemory:
    def __init__(self):
        # A SEPARATE vector store (its own folder + collection) so past solutions
        # never get mixed up with the code index from Phase 5.
        self.store = Chroma(
            persist_directory=settings.memory_db_dir,
            embedding_function=get_embeddings(),
            collection_name="past_issues",
        )

    def remember(self, issue_summary: str, solution: str, memory_id: str) -> None:
        """Save a solved issue. `memory_id` is a stable id so re-saving the same
        issue OVERWRITES instead of creating duplicates."""
        self.store.add_texts(
            texts=[issue_summary],                 # what we search ON (the problem)
            metadatas=[{"solution": solution}],    # what we get back (the fix)
            ids=[memory_id],
        )

    def recall(self, query: str, k: int | None = None) -> list[dict]:
        """Find the most similar PAST issues to help solve the current one."""
        k = k or settings.memory_top_k
        docs = self.store.similarity_search(query, k=k)
        return [
            {"past_issue": d.page_content, "past_solution": d.metadata.get("solution", "")}
            for d in docs
        ]


@lru_cache(maxsize=1)
def get_memory() -> LongTermMemory:
    """One shared memory object for the whole app (built once)."""
    return LongTermMemory()
