"""
phase3_demo.py — build an AGENT by hand so you SEE the loop. Run with:

    python -m scripts.phase3_demo

The big idea:
    An LLM alone can only produce TEXT.
    An AGENT = LLM + TOOLS + a LOOP, where the LLM decides which tool to call,
    reads the result, and keeps going until it can answer.

    That loop is called ReAct = REASON + ACT:
        REASON  -> the model thinks about what to do
        ACT     -> it calls a tool (a Python function)
        OBSERVE -> we run the tool and give it the result
        ...repeat until the model gives a final answer.

We will NOT use a prebuilt agent here — we hand-write the loop so it's not magic.
(In the real project, LangGraph gives us this loop for free — but now you know
what's inside the box.)
"""

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from app.agents.llm import get_llm


# --- STEP 1: Define TOOLS ---------------------------------------------------
# A "tool" is just a Python function the LLM is allowed to call. The @tool
# decorator + the docstring tell the model WHAT it does and WHEN to use it.
# The docstring is not a comment here — the model literally reads it to decide.

@tool
def add(a: int, b: int) -> int:
    """Add two numbers together and return the sum."""
    print(f"   [tool] add({a}, {b})")
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers together and return the product."""
    print(f"   [tool] multiply({a}, {b})")
    return a * b


TOOLS = [add, multiply]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


# --- STEP 2: The agent loop -------------------------------------------------
def run_agent(question: str, max_steps: int = 5):
    llm = get_llm()

    # bind_tools() tells the model "these tools exist, you may request them".
    # The model can now reply with a normal answer OR with "tool_calls".
    llm_with_tools = llm.bind_tools(TOOLS)

    # The conversation memory for THIS run (short-term memory).
    #
    # NOTE the very explicit rules below. Smaller open models (Llama on Groq) are
    # weaker at tool-calling than frontier models and will try to NEST tool calls
    # (e.g. multiply(5, add(3,4))) which is invalid and errors with 'tool_use_failed'.
    # We fix that by telling it to do ONE tool at a time — which is exactly how the
    # ReAct loop is supposed to work: act, observe the result, THEN decide the next act.
    messages = [
        SystemMessage(content=(
            "You are a math assistant that computes step by step.\n"
            "RULES:\n"
            "1. Call only ONE tool at a time.\n"
            "2. NEVER put a tool call inside another tool's arguments. "
            "Arguments must be plain numbers only.\n"
            "3. First compute the inner operation, wait for its result, "
            "then use that number in the next tool call.\n"
            "4. When you have the final number, reply with just the answer."
        )),
        HumanMessage(content=question),
    ]

    for step in range(max_steps):
        print(f"\n-- step {step + 1}: REASON --")
        ai = llm_with_tools.invoke(messages)   # the model thinks
        messages.append(ai)

        # If the model did NOT ask for a tool, it's done -> final answer.
        if not ai.tool_calls:
            print("-- FINAL ANSWER --")
            print(ai.content)
            return ai.content

        # Otherwise, ACT: run each requested tool and OBSERVE the result.
        print("-- ACT: model requested tools --")
        for call in ai.tool_calls:
            fn = TOOLS_BY_NAME[call["name"]]
            result = fn.invoke(call["args"])           # actually run the tool
            # Feed the result back so the model can use it next round:
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    return "Stopped: hit max steps."


if __name__ == "__main__":
    # This forces a 2-step plan: first add, then multiply.
    print("QUESTION: What is (3 + 4) multiplied by 5?")
    run_agent("What is (3 + 4) multiplied by 5? Show the final number.")
    print("\n[DONE] Phase 3: you just watched an agent reason, act, observe, and finish.")
