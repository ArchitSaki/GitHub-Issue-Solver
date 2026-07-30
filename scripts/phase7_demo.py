"""
phase7_demo.py — the agent uses REAL tools to investigate a GitHub issue.

    python -m scripts.phase7_demo

This is the Phase 3 ReAct loop again, but now the tools DO something useful:
read a real issue, list the repo, read the suspect file. Watch the [tool] lines.
"""

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.agents.llm import get_llm
from app.tools.github_tools import GITHUB_TOOLS

TOOLS_BY_NAME = {t.name: t for t in GITHUB_TOOLS}


def run(goal: str, max_steps: int = 6):
    llm = get_llm().bind_tools(GITHUB_TOOLS)

    messages = [
        # Strict rules, because open models nest tool calls otherwise (Phase 3 lesson).
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

    for step in range(max_steps):
        ai = llm.invoke(messages)
        messages.append(ai)

        if not ai.tool_calls:
            print("\n--- AGENT CONCLUSION ---")
            print(ai.content)
            return ai.content

        for call in ai.tool_calls:
            fn = TOOLS_BY_NAME[call["name"]]
            result = fn.invoke(call["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    return "Stopped: hit max steps."


if __name__ == "__main__":
    print("GOAL: investigate issue #42 and find the root cause.\n")
    run("Investigate issue number 42. Find which file causes it and explain the root cause.")
    print("\n[DONE] Phase 7: the agent has hands - it read the issue and the code.")
