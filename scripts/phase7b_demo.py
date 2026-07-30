"""
phase7b_demo.py — the agent investigates issue #42 using tools loaded OVER MCP.

    python -m scripts.phase7b_demo

Compare with phase7_demo.py:
    phase7_demo.py  -> imports tools directly from app/tools/github_tools.py
    phase7b_demo.py -> DISCOVERS tools from the running MCP server (the real protocol)

Same agent, same result — but the tools now arrive through MCP.
"""

import asyncio

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.agents.llm import get_llm
from app.tools.mcp_client import load_mcp_tools


async def run(goal: str, max_steps: int = 6):
    # 1. CONNECT to the MCP server and DISCOVER its tools (no hard-coded list).
    print("[mcp] starting server + discovering tools...")
    tools = await load_mcp_tools()
    print(f"[mcp] discovered {len(tools)} tools: {[t.name for t in tools]}\n")

    tools_by_name = {t.name: t for t in tools}
    llm = get_llm().bind_tools(tools)

    messages = [
        SystemMessage(content=(
            "You are a software engineer investigating a GitHub issue.\n"
            "RULES:\n"
            "1. Call ONE tool at a time and wait for its result.\n"
            "2. NEVER nest a tool call inside another tool's arguments.\n"
            "3. Typical order: get_issue -> list_repo_files -> read_repo_file.\n"
            "4. When you know the root cause, STOP calling tools and explain it briefly."
        )),
        HumanMessage(content=goal),
    ]

    for _ in range(max_steps):
        ai = await llm.ainvoke(messages)      # async because MCP tools are async
        messages.append(ai)

        if not ai.tool_calls:
            print("--- AGENT CONCLUSION (via MCP tools) ---")
            print(ai.content)
            return ai.content

        for call in ai.tool_calls:
            tool = tools_by_name[call["name"]]
            print(f"   [mcp tool] {call['name']}({call['args']})")
            result = await tool.ainvoke(call["args"])   # goes over JSON-RPC to the server
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    return "Stopped: hit max steps."


if __name__ == "__main__":
    asyncio.run(run(
        "Investigate issue number 42. Find which file causes it and explain the root cause."
    ))
    print("\n[DONE] Phase 7b: the agent used tools THROUGH the MCP protocol.")
