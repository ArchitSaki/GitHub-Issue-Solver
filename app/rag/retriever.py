"""
retriever.py — search the code index (the "R" = Retrieval in RAG).

Given a question (like an issue), we find the top-k most RELEVANT code chunks.
This is what keeps our context window small and our token bill low: instead of
sending the whole repo to the LLM, we send only these few chunks.
"""

from functools import lru_cache

from langchain_chroma import Chroma

from app.agents.llm import get_embeddings
from app.config import settings


@lru_cache(maxsize=1)
def _get_store() -> Chroma:
    """Open the on-disk vector DB once and reuse it (lower latency)."""
    return Chroma(
        persist_directory=settings.vector_db_dir,
        embedding_function=get_embeddings(),
    )


def search_code(query: str, k: int | None = None) -> list[dict]:
    """Return the top-k relevant code chunks for a query.

    Each result is {source, snippet}. k defaults to RAG_TOP_K from .env
    (small on purpose = fewer tokens).
    """
    k = k or settings.rag_top_k
    store = _get_store()

    # similarity_search embeds the query and finds the nearest chunk vectors.
    results = store.similarity_search(query, k=k)

    return [
        {"source": doc.metadata.get("source", "?"), "snippet": doc.page_content}
        for doc in results
    ]


def format_context(chunks: list[dict]) -> str:
    """Turn retrieved chunks into a compact string to put in a prompt."""
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"--- chunk {i} (from {c['source']}) ---\n{c['snippet']}")
    return "\n\n".join(parts)
