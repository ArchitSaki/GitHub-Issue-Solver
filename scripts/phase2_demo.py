"""
phase2_demo.py — your first real LLM calls. Run it with:

    python -m scripts.phase2_demo

It shows THREE things, from simplest to most useful:
    1) A plain message call        (the raw way)
    2) A prompt template           (the reusable way)
    3) Structured output           (the RELIABLE way we'll actually use)
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agents.llm import get_llm


def demo_1_plain_call():
    print("\n=== 1) PLAIN MESSAGE CALL ===")
    llm = get_llm()

    # An LLM chat is a LIST OF MESSAGES with roles:
    #   SystemMessage = the rules / persona ("you are X, do Y")
    #   HumanMessage  = what the user says
    #   (AIMessage    = what the model replies — we get this back)
    messages = [
        SystemMessage(content="You are a concise senior software engineer."),
        HumanMessage(content="In one sentence, what is a GitHub issue?"),
    ]

    # .invoke() = "run once, give me the answer". Returns an AIMessage.
    reply = llm.invoke(messages)
    print("LLM says:", reply.content)


def demo_2_prompt_template():
    print("\n=== 2) PROMPT TEMPLATE (reusable) ===")
    llm = get_llm()

    # A template has {placeholders} we fill in later. This avoids messy string
    # concatenation and keeps prompts consistent (and short = fewer tokens).
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a concise senior software engineer."),
        ("human", "Explain '{topic}' to a junior dev in one sentence."),
    ])

    # The "|" pipe chains steps: fill prompt -> send to llm. This is "LCEL"
    # (LangChain Expression Language). chain.invoke fills {topic} and runs it.
    chain = prompt | llm
    reply = chain.invoke({"topic": "Retrieval Augmented Generation"})
    print("LLM says:", reply.content)


# --- For demo 3, we define the EXACT shape we want back --------------------
class IssueSummary(BaseModel):
    """A clean, structured understanding of a GitHub issue."""
    title: str = Field(description="a short title for the problem")
    problem: str = Field(description="one sentence describing the bug/request")
    is_bug: bool = Field(description="true if it's a bug, false if a feature request")
    keywords: list[str] = Field(description="2-4 code-search keywords")


def demo_3_structured_output():
    print("\n=== 3) STRUCTURED OUTPUT (reliable, machine-readable) ===")
    llm = get_llm()

    # .with_structured_output() FORCES the model to return data matching our
    # Pydantic class — no messy text parsing, no "please output JSON" begging.
    # This is HOW our agents will pass clean data between steps.
    structured_llm = llm.with_structured_output(IssueSummary)

    raw_issue = (
        "Title: App crashes on login\n"
        "When I click 'Login' with an empty email field, the whole app crashes "
        "with a NullPointerException instead of showing a validation error."
    )

    result = structured_llm.invoke(
        f"Summarize this GitHub issue into the required structure:\n\n{raw_issue}"
    )
    # 'result' is now a real IssueSummary object with typed fields:
    print("title    :", result.title)
    print("problem  :", result.problem)
    print("is_bug   :", result.is_bug)
    print("keywords :", result.keywords)


if __name__ == "__main__":
    demo_1_plain_call()
    demo_2_prompt_template()
    demo_3_structured_output()
    print("\n[DONE] Phase 2 works! Your code can talk to the LLM.")
