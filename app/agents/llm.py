"""
llm.py — the "brain factory".

WHY THIS FILE EXISTS:
    The rest of our project should NOT care whether we use Groq, OpenAI, Claude,
    or a local model. It should just say "give me a model" and "give me embeddings".
    This file hides those details behind two simple functions:

        get_llm()         -> a chat model for REASONING (Groq by default)
        get_embeddings()  -> a local model that turns text into vectors (for RAG)

    This is the "Factory pattern" + "Dependency inversion" — swapping providers
    means editing ONE file (or just the .env), not the whole codebase.
    (Great interview point: "I kept the LLM provider swappable behind a factory.")
"""

from functools import lru_cache

from app.config import settings


# lru_cache = build the model ONCE and reuse it. Creating a client every call
# is wasteful (re-opens connections). Reusing it lowers latency. Token/cost win too.
@lru_cache(maxsize=1)
def get_llm(temperature: float = 0.0):
    """
    Returns a LangChain chat model based on LLM_PROVIDER in .env.

    temperature = 0.0 means "be deterministic / factual" (good for code).
    Higher (e.g. 0.7) = more creative/random. For fixing bugs we want 0.
    """
    provider = settings.llm_provider.lower()

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=temperature,
            # max_tokens caps the REPLY length -> protects us from runaway token use.
            max_tokens=1024,
            timeout=60,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            api_key=settings.anthropic_api_key,
            temperature=temperature,
            max_tokens=1024,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.openai_api_key,
            temperature=temperature,
            max_tokens=1024,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")


@lru_cache(maxsize=1)
def get_embeddings():
    """
    Returns a LOCAL embedding model (FastEmbed). Used in Phase 5 (RAG).
    Runs on your machine, free, downloads a ~90MB model on first use.

    An "embedding" is a list of numbers that represents the MEANING of text,
    so we can find code that is "similar in meaning" to an issue.
    """
    from langchain_community.embeddings import FastEmbedEmbeddings
    return FastEmbedEmbeddings(model_name=settings.embed_model)
