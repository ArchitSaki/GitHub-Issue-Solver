"""
config.py — one place that reads all our settings from the .env file.

WHY THIS FILE EXISTS:
    Instead of scattering "http://localhost:11434" or model names all over the
    codebase, we read them ONCE here. If you want to change the model, you edit
    the .env file — not 20 different Python files. This is called
    "centralized configuration" and interviewers love seeing it.

HOW IT WORKS:
    pydantic-settings automatically reads matching names from the .env file
    (e.g. the field `llm_provider` is filled from `LLM_PROVIDER` in .env).
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Tell pydantic to load from a file named ".env" and ignore extra keys.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM provider (for reasoning/chat) ---
    llm_provider: str = "groq"            # "groq" | "anthropic" | "openai" | "ollama"

    # --- Groq (fast cloud, free tier) ---
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # --- Embeddings (local + free, for RAG) ---
    embed_model: str = "BAAI/bge-small-en-v1.5"

    # --- Other providers (optional) ---
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ollama_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"

    # --- GitHub ---
    github_mode: str = "mock"             # "mock" | "real"
    github_token: str = ""
    github_repo: str = "owner/repo"       # only used when github_mode == "real"

    @field_validator("github_repo")
    @classmethod
    def clean_github_repo(cls, v: str) -> str:
        """Strip https://github.com/ and .git if accidentally included."""
        v = v.strip()
        for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
            if v.startswith(prefix):
                v = v[len(prefix):]
        if v.endswith(".git"):
            v = v[:-4]
        return v.strip("/")

    # --- RAG ---
    vector_db_dir: str = ".vectordb"
    rag_top_k: int = 4

    # --- Long-term memory (separate vector store of past solved issues) ---
    memory_db_dir: str = ".memorydb"
    memory_top_k: int = 2


# A single shared settings object the whole app imports:  from app.config import settings
settings = Settings()


# Quick self-test: run `python -m app.config` to print the loaded settings.
if __name__ == "__main__":
    print("Loaded settings:")
    for key, value in settings.model_dump().items():
        # Hide secrets when printing.
        if "key" in key or "token" in key:
            value = "***set***" if value else "(empty)"
        print(f"  {key:20} = {value}")
