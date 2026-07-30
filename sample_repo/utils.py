"""Generic string/format helpers (unrelated to the login bug)."""


def slugify(text: str) -> str:
    return text.strip().lower().replace(" ", "-")


def truncate(text: str, limit: int = 80) -> str:
    return text if len(text) <= limit else text[:limit] + "..."
