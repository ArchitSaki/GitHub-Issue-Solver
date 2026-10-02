"""
indexer.py — build a searchable index of a codebase (the "R" setup in RAG).

THE RAG PIPELINE (memorize this — interviewers ask it constantly):

    1. LOAD    : read the code files from disk
    2. SPLIT   : cut each file into small "chunks" (so results are focused)
    3. EMBED   : turn each chunk into a vector (a list of numbers = its meaning)
    4. STORE   : save those vectors in a vector database (Chroma)

Later (retriever.py) we EMBED the question and find the chunks whose vectors are
closest = most similar in meaning. That's "semantic search".

WHY chunk? If we stored whole files, a match would drag in lots of irrelevant code
(wasted tokens). Small chunks = we feed the LLM only the relevant lines.
"""

import shutil
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from app.agents.llm import get_embeddings
from app.config import settings

# Which file types count as "code" we want to index.
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".java", ".go", ".md", ".txt"}


def _load_files(repo_dir: str) -> list[Document]:
    """STEP 1 - LOAD: read every code file into a Document (text + metadata)."""
    docs = []
    for path in Path(repo_dir).rglob("*"):
        if path.is_file() and path.suffix in CODE_EXTENSIONS:
            text = path.read_text(encoding="utf-8", errors="ignore")
            # metadata lets us show WHERE a chunk came from (the file path).
            docs.append(Document(page_content=text, metadata={"source": str(path)}))
    return docs


def _split(docs: list[Document]) -> list[Document]:
    """STEP 2 - SPLIT: cut files into overlapping chunks.

    chunk_size    = max characters per chunk (small = focused, fewer tokens).
    chunk_overlap = repeat a few chars between chunks so we don't cut a function
                    in half and lose context at the seam.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
    )
    return splitter.split_documents(docs)


def build_index(repo_dir: str = "sample_repo") -> int:
    """Run the whole pipeline and save the index to disk. Returns #chunks stored."""
    print(f"[rag] indexing '{repo_dir}' ...")

    # Start fresh each time so we don't pile up duplicate vectors on re-runs.
    db_path = Path(settings.vector_db_dir)
    if db_path.exists():
        shutil.rmtree(db_path)

    docs = _load_files(repo_dir)          # 1. LOAD
    chunks = _split(docs)                  # 2. SPLIT
    print(f"[rag] {len(docs)} files -> {len(chunks)} chunks")

    if not chunks:
        print(f"[rag] WARNING: No code chunks found in '{repo_dir}'. Index was not created.")
        return 0

    # 3. EMBED + 4. STORE happen together: Chroma embeds each chunk and saves it.
    Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),        # our local FastEmbed model
        persist_directory=settings.vector_db_dir,
    )
    print(f"[rag] index saved to '{settings.vector_db_dir}'")
    return len(chunks)


if __name__ == "__main__":
    n = build_index()
    print(f"[DONE] indexed {n} chunks.")
