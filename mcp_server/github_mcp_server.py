"""
github_mcp_server.py — expose our GitHub tools over the REAL Model Context Protocol.

WHY THIS FILE EXISTS:
    In app/tools/github_tools.py the tools are normal Python functions our agent calls
    in-process. That is fast, but the tools are locked inside OUR app.

    MCP (Model Context Protocol) is an open STANDARD for exposing tools to ANY AI client.
    By wrapping the same functions in an MCP server, our tools can also be used by
    Claude Desktop, Cursor, or any other MCP-compatible client — without changing them.

    Think of MCP as "USB-C for AI tools": one standard plug, many devices.

HOW MCP WORKS (say this in interviews):
    - An MCP SERVER exposes three things: TOOLS (actions), RESOURCES (readable data),
      and PROMPTS (reusable templates).
    - An MCP CLIENT (the AI app) connects and calls them using JSON-RPC messages,
      usually over stdio (a local subprocess) or HTTP.
    - The client discovers what's available at runtime ("list tools"), so you can add
      a tool to the server and clients see it without a code change.

RUN IT:
    pip install mcp
    python -m mcp_server.github_mcp_server

    (It runs as a stdio server and waits for a client — that's expected, not a hang.)
"""

from mcp.server.fastmcp import FastMCP

# We reuse the SAME logic as our in-process tools. `.invoke({...})` calls the
# underlying LangChain tool. Single source of truth = no duplicated logic.
from app.tools.github_tools import (
    get_issue as _get_issue,
    list_repo_files as _list_repo_files,
    read_repo_file as _read_repo_file,
    open_pull_request as _open_pull_request,
)

# Create the MCP server. The name identifies it to clients.
mcp_app = FastMCP("github-issue-solver")


# The @mcp_app.tool() decorator publishes a function as an MCP tool.
# Just like LangChain tools, the DOCSTRING is what the AI reads to decide usage.
@mcp_app.tool()
def get_issue(issue_number: int) -> str:
    """Fetch a GitHub issue by number. Returns title, labels and body."""
    return _get_issue.invoke({"issue_number": issue_number})


@mcp_app.tool()
def list_repo_files() -> str:
    """List the code files available in the repository."""
    return _list_repo_files.invoke({})


@mcp_app.tool()
def read_repo_file(path: str) -> str:
    """Read the contents of one file in the repository."""
    return _read_repo_file.invoke({"path": path})


@mcp_app.tool()
def open_pull_request(title: str, body: str, file_path: str, new_content: str) -> str:
    """Open a pull request replacing file_path with new_content."""
    return _open_pull_request.invoke({
        "title": title,
        "body": body,
        "file_path": file_path,
        "new_content": new_content,
    })


if __name__ == "__main__":
    # "stdio" transport = the client launches this file as a subprocess and talks
    # to it over standard input/output. This is the most common local MCP setup.
    mcp_app.run(transport="stdio")
