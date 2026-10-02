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

import base64
import json
from pathlib import Path
import time

import requests
from langchain_core.tools import tool

from app.config import settings

# Where our fake repo + fake issues live in mock mode.
MOCK_REPO_DIR = Path("sample_repo")
MOCK_ISSUES_FILE = Path("mock_data/issues.json")
MOCK_PR_DIR = Path(".mock_prs")


def _github_headers() -> dict[str, str]:
    """Headers required by GitHub REST API."""
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_default_branch() -> str:
    """Fetch the default branch (e.g. main or master) of the configured repo."""
    url = f"https://api.github.com/repos/{settings.github_repo}"
    resp = requests.get(url, headers=_github_headers(), timeout=20)
    resp.raise_for_status()
    return resp.json().get("default_branch", "main")


def _get_branch_sha(branch: str) -> str:
    """Fetch the latest commit SHA of a branch."""
    url = f"https://api.github.com/repos/{settings.github_repo}/git/ref/heads/{branch}"
    resp = requests.get(url, headers=_github_headers(), timeout=20)
    resp.raise_for_status()
    return resp.json()["object"]["sha"]


def _create_branch(new_branch: str, base_sha: str) -> None:
    """Create a new branch pointing to base_sha."""
    url = f"https://api.github.com/repos/{settings.github_repo}/git/refs"
    resp = requests.post(
        url,
        headers=_github_headers(),
        json={"ref": f"refs/heads/{new_branch}", "sha": base_sha},
        timeout=20,
    )
    resp.raise_for_status()


def _find_github_file_path(path: str, branch: str) -> tuple[str, str | None]:
    """Resolve the repository-relative file path and fetch its current blob SHA if it exists.

    Why this matters: Local RAG may index paths like 'sample_repo/auth.py' or 'target_repo/auth.py'.
    On GitHub, the file path relative to repo root is 'auth.py'. We normalize and probe GitHub.
    """
    clean_path = path.replace("\\", "/").strip("/")
    candidates = [clean_path]
    parts = clean_path.split("/")
    if len(parts) > 1:
        candidates.append("/".join(parts[1:]))

    headers = _github_headers()
    for candidate in candidates:
        url = f"https://api.github.com/repos/{settings.github_repo}/contents/{candidate}?ref={branch}"
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            return candidate, resp.json().get("sha")

    # If it's a newly created file, default to the trimmed candidate
    return (candidates[-1] if len(candidates) > 1 else clean_path), None


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
        resp = requests.get(url, headers=_github_headers(), timeout=20)
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

    if settings.github_mode == "mock":
        files = [str(p) for p in MOCK_REPO_DIR.rglob("*") if p.is_file()]
        return "\n".join(files) if files else "(no files)"

    # REAL MODE: fetch the full file tree from GitHub API
    try:
        default_branch = _get_default_branch()
        url = f"https://api.github.com/repos/{settings.github_repo}/git/trees/{default_branch}?recursive=1"
        resp = requests.get(url, headers=_github_headers(), timeout=20)
        resp.raise_for_status()
        tree = resp.json().get("tree", [])
        files = [item["path"] for item in tree if item.get("type") == "blob"]
        return "\n".join(files) if files else "(no files)"
    except Exception as exc:
        return f"Error listing repository files from GitHub: {exc}"


# ---------------------------------------------------------------------------
# TOOL 3: read one file
# ---------------------------------------------------------------------------
@tool
def read_repo_file(path: str) -> str:
    """Read the full contents of ONE file in the repository, given its path."""
    print(f"   [tool] read_repo_file({path})")
    p = Path(path)

    # 1. Try local filesystem first (fastest, works when repo is cloned locally)
    if p.exists() and p.is_file():
        text = p.read_text(encoding="utf-8", errors="ignore")
    elif settings.github_mode == "real":
        # 2. In real mode, fetch remotely from GitHub contents API if not found locally
        try:
            default_branch = _get_default_branch()
            target_path, _ = _find_github_file_path(path, default_branch)
            url = f"https://api.github.com/repos/{settings.github_repo}/contents/{target_path}?ref={default_branch}"
            resp = requests.get(url, headers=_github_headers(), timeout=20)
            if resp.status_code == 200:
                raw_b64 = resp.json().get("content", "")
                text = base64.b64decode(raw_b64).decode("utf-8", errors="ignore")
            else:
                return f"File not found locally or on GitHub: {path}"
        except Exception as exc:
            return f"Error fetching file from GitHub: {exc}"
    else:
        return f"File not found: {path}"

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

    # REAL MODE: create branch -> commit file -> create pull request via GitHub REST API
    if not settings.github_token:
        return "Error: GITHUB_TOKEN is not configured in .env."
    if not settings.github_repo or settings.github_repo == "owner/repo":
        return "Error: GITHUB_REPO is not configured properly in .env (format: 'owner/repo')."

    try:
        # Step 1: get base branch & SHA
        default_branch = _get_default_branch()
        base_sha = _get_branch_sha(default_branch)

        # Step 2: create a unique branch for this fix
        branch_name = f"fix-solver-{int(time.time())}"
        _create_branch(branch_name, base_sha)

        # Step 3: locate file in repo & commit the change
        target_path, file_sha = _find_github_file_path(file_path, default_branch)
        commit_url = f"https://api.github.com/repos/{settings.github_repo}/contents/{target_path}"
        commit_payload = {
            "message": f"Fix: {title}",
            "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
            "branch": branch_name,
        }
        if file_sha:
            commit_payload["sha"] = file_sha

        commit_resp = requests.put(
            commit_url,
            headers=_github_headers(),
            json=commit_payload,
            timeout=20,
        )
        commit_resp.raise_for_status()

        # Step 4: open the Pull Request
        pr_url = f"https://api.github.com/repos/{settings.github_repo}/pulls"
        pr_payload = {
            "title": title,
            "body": f"{body}\n\n---\n*Automated PR opened by Agentic GitHub Issue Solver*",
            "head": branch_name,
            "base": default_branch,
        }
        pr_resp = requests.post(
            pr_url,
            headers=_github_headers(),
            json=pr_payload,
            timeout=20,
        )
        pr_resp.raise_for_status()
        pr_data = pr_resp.json()

        return f"[real] Pull request #{pr_data['number']} created: {pr_data['html_url']}"
    except Exception as exc:
        return f"Failed to create real pull request: {exc}"


# All tools in one list so the agent/graph can import them easily.
GITHUB_TOOLS = [get_issue, list_repo_files, read_repo_file, open_pull_request]
