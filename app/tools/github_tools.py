"""
github_tools.py — the agent's HANDS: tools to read issues, read code, and open PRs.

WHY TOOLS?
    An LLM can only produce text. Tools are the Python functions we ALLOW it to call
    so it can affect the real world (read a repo, open a Pull Request).

MOCK vs REAL (set GITHUB_MODE in .env):
    mock -> reads from mock_data/issues.json + the local sample_repo/ folder, and
            "opens a PR" by writing a patch file to .mock_prs/. No token needed.
    real -> talks to the actual GitHub REST API using GITHUB_TOKEN.

    Why build mock first? We can develop and test the whole agent end-to-end with
    ZERO network calls, ZERO tokens, and no risk of writing to a real repo.
    Swapping in the real API later changes only this file. (Interview point:
    "I isolated external I/O behind a tool layer so it was testable and swappable.")
"""

import json
from pathlib import Path

import requests
from langchain_core.tools import tool

from app.config import settings

# Where our fake repo + fake issues live in mock mode.
MOCK_REPO_DIR = Path("sample_repo")
MOCK_ISSUES_FILE = Path("mock_data/issues.json")
MOCK_PR_DIR = Path(".mock_prs")


# ---------------------------------------------------------------------------
# TOOL 1: read an issue
# ---------------------------------------------------------------------------
@tool
def get_issue(issue_number: int) -> str:
    """Fetch a GitHub issue by its number. Returns the title, body and labels."""
    print(f"   [tool] get_issue({issue_number})")

    if settings.github_mode == "mock":
        issues = json.loads(MOCK_ISSUES_FILE.read_text(encoding="utf-8"))
        issue = issues.get(str(issue_number))
        if not issue:
            return f"Issue #{issue_number} not found."
    else:
        # REAL MODE: call the GitHub REST API.
        url = f"https://api.github.com/repos/{settings.github_repo}/issues/{issue_number}"
        headers = {"Authorization": f"Bearer {settings.github_token}"}
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        issue = {
            "title": data["title"],
            "body": data.get("body") or "",
            "labels": [l["name"] for l in data.get("labels", [])],
        }

    return (
        f"Title: {issue['title']}\n"
        f"Labels: {', '.join(issue['labels'])}\n"
        f"Body: {issue['body']}"
    )


# ---------------------------------------------------------------------------
# TOOL 2: list the files in the repo
# ---------------------------------------------------------------------------
@tool
def list_repo_files() -> str:
    """List the code files available in the repository."""
    print("   [tool] list_repo_files()")
    files = [str(p) for p in MOCK_REPO_DIR.rglob("*") if p.is_file()]
    return "\n".join(files) if files else "(no files)"


# ---------------------------------------------------------------------------
# TOOL 3: read one file
# ---------------------------------------------------------------------------
@tool
def read_repo_file(path: str) -> str:
    """Read the full contents of ONE file in the repository, given its path."""
    print(f"   [tool] read_repo_file({path})")
    p = Path(path)
    if not p.exists():
        return f"File not found: {path}"
    text = p.read_text(encoding="utf-8", errors="ignore")

    # Keep tool output SMALL — every character comes back into the context window
    # and costs tokens. Truncate very large files.
    if len(text) > 4000:
        text = text[:4000] + "\n... (truncated)"
    return text


# ---------------------------------------------------------------------------
# TOOL 4: open a pull request with the fix
# ---------------------------------------------------------------------------
@tool
def open_pull_request(title: str, body: str, file_path: str, new_content: str) -> str:
    """Open a pull request that replaces file_path with new_content.

    Use this only AFTER you have written the corrected file content.
    """
    print(f"   [tool] open_pull_request(title={title!r}, file={file_path})")

    if settings.github_mode == "mock":
        # "Opening a PR" in mock mode = save the proposed change locally so we can
        # inspect it. Safe, free, and fully testable.
        MOCK_PR_DIR.mkdir(exist_ok=True)
        safe_name = file_path.replace("\\", "_").replace("/", "_")
        out = MOCK_PR_DIR / f"PR__{safe_name}.md"
        out.write_text(
            f"# {title}\n\n{body}\n\n## Proposed content for `{file_path}`\n\n"
            f"```python\n{new_content}\n```\n",
            encoding="utf-8",
        )
        return f"[mock] Pull request saved to {out}"

    # REAL MODE would: create a branch, commit the new file content, then POST to
    # /repos/{repo}/pulls. Left as the productionisation step (needs a real repo).
    return "Real PR creation is not enabled. Set GITHUB_MODE=mock or implement it."


# All tools in one list so the agent/graph can import them easily.
GITHUB_TOOLS = [get_issue, list_repo_files, read_repo_file, open_pull_request]
