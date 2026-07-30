# llm.md — Phase 2: Talking to the LLM (LangChain basics)

> Goal: understand how our code sends text to a model and gets an answer back,
> in a clean, reusable, token-efficient way. Everything later (agents, RAG,
> LangGraph) is built on these basics.

Files in this phase:
- `app/agents/llm.py` — the "brain factory" (`get_llm`, `get_embeddings`)
- `scripts/phase2_demo.py` — runnable examples

---

## 1. What is LangChain, really?

LangChain is a **toolkit that gives every LLM provider the same interface**, plus
building blocks (prompts, chains, tools, memory, RAG helpers).

Without LangChain, Groq's SDK, OpenAI's SDK, and Claude's SDK all look different.
With LangChain, you write `llm.invoke(...)` once and can swap providers by changing
one line. **That's why our `llm.py` factory can support 4 providers with the same code.**

## 2. The 3 core ideas

### (a) Messages have roles
A chat is a **list of messages**, each with a role:
| Role | Class | Meaning |
|------|-------|---------|
| system | `SystemMessage` | the rules/persona: "You are a senior engineer, be concise" |
| user | `HumanMessage` | what we ask |
| assistant | `AIMessage` | what the model replies (we receive this) |

`llm.invoke([...messages...])` returns an `AIMessage`; the text is in `.content`.

> **Why the system message matters (token tip):** a good short system message makes
> answers shorter and more on-target → fewer output tokens → cheaper + faster.

### (b) Prompt templates = reusable prompts
Instead of gluing strings together, we use a template with `{placeholders}`:
```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are concise."),
    ("human", "Explain '{topic}' in one sentence."),
])
chain = prompt | llm            # the "|" pipes prompt -> llm
chain.invoke({"topic": "RAG"})  # fills the blank and runs
```
The `|` pipe is **LCEL** (LangChain Expression Language). Think of it like a Unix
pipe: output of the left becomes input of the right. We chain: `prompt | llm | parser`.

### (c) Structured output = reliable data, not loose text
Normally an LLM returns free text, which is annoying to parse. Instead we define the
shape we want with **Pydantic** and force the model to fill it:
```python
class IssueSummary(BaseModel):
    title: str
    is_bug: bool
    keywords: list[str]

structured_llm = llm.with_structured_output(IssueSummary)
result = structured_llm.invoke("Summarize: ...")
result.keywords   # -> a real Python list, guaranteed
```
**This is the single most important trick in the whole project.** Our agents pass
clean, typed data between steps using this — no fragile text parsing.

## 3. Design choices in `llm.py` (and why)

| Choice | Why | Interview soundbite |
|--------|-----|---------------------|
| Factory function `get_llm()` | Rest of app is provider-agnostic | "Provider swappable behind a factory" |
| `@lru_cache` | Build the client once, reuse it | "Reuse clients to cut latency & overhead" |
| `temperature=0.0` | Deterministic, factual — right for code | "Low temp for correctness-critical tasks" |
| `max_tokens=1024` | Caps reply length | "Bounded output to control cost/latency" |
| Local `get_embeddings()` | Groq has no embeddings; keep RAG free | "Local embeddings + cloud reasoning split" |

## 4. Run it

```powershell
# make sure your venv is active and GROQ_API_KEY is set in .env
python -m scripts.phase2_demo
```
Expected: three sections print, ending with "✅ Phase 2 works!".

Common errors:
- `AuthenticationError / 401` → your `GROQ_API_KEY` in `.env` is missing/wrong.
- `ModuleNotFoundError` → venv not active, or `pip install -r requirements.txt` not run.
- Model name error → the Groq model was renamed; pick a current one from console.groq.com.

## 5. Interview questions you can now answer

- **Q: What does LangChain give you over calling the provider SDK directly?**
  A unified interface across providers, plus prompts/chains/tools/memory/RAG helpers,
  so components are swappable and composable.
- **Q: How do you get reliable JSON/data out of an LLM?**
  `with_structured_output(PydanticModel)` — the framework enforces the schema via the
  model's tool/function-calling, so I get typed objects, not text to regex.
- **Q: How do you control cost and latency at the call level?**
  Short system prompts, `temperature=0`, `max_tokens` caps, client reuse (caching),
  and picking a smaller/faster model for easy steps.
- **Q: What is temperature?**
  Randomness of output. 0 = deterministic (good for code/facts), higher = creative.

✅ Phase 2 done when `scripts/phase2_demo.py` prints all three demos successfully.
