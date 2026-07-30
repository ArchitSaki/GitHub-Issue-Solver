"""
mcp_client.py — the OTHER half of MCP: our agent acting as an MCP CLIENT.

WHY THIS FILE EXISTS:
    mcp_server/github_mcp_server.py PUBLISHES our tools over the MCP standard.
    But publishing alone doesn't mean our agent "uses MCP" — something has to
    CONNECT to that server and call the tools through the protocol.

    That's this file. It:
      1. launches the MCP server as a subprocess (stdio transport),
      2. asks it "what tools do you have?" (runtime DISCOVERY),
      3. converts them into LangChain tools our agent can call.

    Now the flow is truly:
        agent  ->  MCP client  ->[JSON-RPC]->  MCP server  ->  GitHub/files

WHY IS THIS ASYNC?
    MCP talks over a live connection (stdio pipes), so the SDK is async.
    That fits FastAPI (Phase 9), which is async too.

TRADE-OFF (be able to say this):
    Direct in-process tools  = fastest (plain function call).
    MCP tools                = a subprocess + JSON-RPC hop, slightly slower,
                               but interoperable and discoverable at runtime.
"""

import sys

from langchain_mcp_adapters.client import MultiServerMCPClient


def _server_config() -> dict:
    """Tell the MCP client HOW to start our server.

    We use sys.executable (the current venv's python) so the subprocess has the
    same dependencies. transport="stdio" = talk over the subprocess's stdin/stdout.
    """
    return {
        "github": {
            "command": sys.executable,
            "args": ["-m", "mcp_server.github_mcp_server"],
            "transport": "stdio",
        }
    }


async def load_mcp_tools() -> list:
    """Connect to the MCP server and return its tools as LangChain tools.

    NOTE: we never hard-code the tool list here. We DISCOVER whatever the server
    offers. Add a tool to the server and the agent can use it with no client change
    — that is the core benefit of MCP.
    """
    client = MultiServerMCPClient(_server_config())
    tools = await client.get_tools()
    return tools
