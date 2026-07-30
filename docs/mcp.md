# mcp.md — Phase 7: Tools + MCP (giving the agent hands)

> The agent could think (LLM), search code (RAG) and remember (memory).
> Now it can ACT: read issues, read files, open PRs — and we expose those tools
> over the open **Model Context Protocol** standard.

Files: `app/tools/github_tools.py`, `mcp_server/github_mcp_server.py`,
`scripts/phase7_demo.py`, `mock_data/issues.json`.

---

## 1. What is MCP, in plain words?

**MCP = Model Context Protocol** — an open standard for how an AI app connects to
tools and data. Think **"USB-C for AI tools"**: one standard plug, many devices.

**The problem it solves:** before MCP, every AI app had its own tool format. A GitHub
integration written for one app didn't work in another — N apps × M tools = N×M custom
integrations. With MCP you write the tool server **once** and any MCP client can use it.

```
   MCP CLIENT                         MCP SERVER
   (Claude Desktop, Cursor,  ──JSON-RPC──►  (our github_mcp_server.py)
    our own agent)            stdio/HTTP     └──► GitHub / files
```

### The three things an MCP server can expose
| Concept | Meaning | Our example |
|---------|---------|-------------|
| **Tools** | actions the AI can perform | `get_issue`, `open_pull_request` |
| **Resources** | readable data/context | repo files (could be exposed this way) |
| **Prompts** | reusable prompt templates | e.g. a "review this diff" template |

Clients **discover** these at runtime ("list tools"), so adding a tool to the server
makes it available without changing the client. We proved this works — our server
reports all 4 tools when queried.

## 2. MCP has TWO halves — you need both to say "my agent uses MCP"

A very common mistake (we made it first, then fixed it): building only the **server**.
Publishing tools over MCP proves *other* clients COULD use them — it does **not** mean
your agent speaks MCP. Something must **connect** and call them through the protocol.

| Half | File | Role |
|------|------|------|
| **MCP SERVER** | `mcp_server/github_mcp_server.py` | publishes tools over the standard |
| **MCP CLIENT** | `app/tools/mcp_client.py` | our agent connects, **discovers**, and calls them |

```
agent ──► MCP client ──JSON-RPC/stdio──► MCP server ──► GitHub / files
```

Proof it's genuine — the server logs real protocol traffic when the agent runs:
```
ListToolsRequest   <- agent DISCOVERING tools at runtime
CallToolRequest    <- agent INVOKING a tool over JSON-RPC
```
The client never hard-codes the tool list. It asks the server what exists. Add a tool
to the server and the agent can use it **with no client change** — that's the whole point.

## 3. Our three layers (and why each exists)

| Layer | File | How it's called | Why |
|-------|------|-----------------|-----|
| **In-process tools** | `app/tools/github_tools.py` | direct Python call | **fastest** — no extra process hop. Our graph uses this on the hot path. |
| **MCP server** | `mcp_server/github_mcp_server.py` | JSON-RPC over stdio | **interoperable** — any MCP client can use the same tools. |
| **MCP client** | `app/tools/mcp_client.py` | `await load_mcp_tools()` | lets **our** agent consume tools over the standard. |

All three share the SAME underlying functions — single source of truth, no duplicated logic.

Compare the two demos:
```powershell
python -m scripts.phase7_demo    # tools imported directly  (fast path)
python -m scripts.phase7b_demo   # tools discovered via MCP (standard path)
```
Same agent, same conclusion — different tool transport.

> **The trade-off (a strong interview answer):** MCP adds a process/serialization hop,
> so it's slightly slower than calling a Python function directly. I use in-process tools
> on the hot path for latency, and expose the same tools via MCP for interoperability.
> *Knowing when NOT to use a buzzword is what makes you sound senior.*

## 3. Mock mode vs real mode

`GITHUB_MODE` in `.env` switches behaviour:
- **mock** — issues come from `mock_data/issues.json`, code from `sample_repo/`, and
  "opening a PR" writes a file into `.mock_prs/`.
- **real** — calls the GitHub REST API with `GITHUB_TOKEN`.

**Why mock first?** We can build and test the whole agent end-to-end with zero network
calls, zero cost, and no risk of writing to a real repo. Swapping to real changes only
this one file.
> Interview point: *"I isolated all external I/O behind a tool layer, so it was testable
> offline and swappable without touching the agent logic."*

## 4. Token/latency discipline in tools

- **Truncate tool output** (`read_repo_file` caps at 4000 chars). Every character a tool
  returns goes back into the context window and costs tokens.
- **Few, sharp tools** beat many vague ones — less model confusion, fewer wasted steps.
- **Cap the loop** (`max_steps`) so a confused agent can't call tools forever.

## 5. What the demo proved

`python -m scripts.phase7_demo` output:
```
[tool] get_issue(42)
[tool] list_repo_files()
[tool] read_repo_file(sample_repo/auth.py)
-> "login() doesn't check for an empty email before splitting it -> IndexError"
```
Nobody told it to open `auth.py`. It read the issue, chose what to inspect, and found
the root cause on its own. **That is agentic behaviour.**

## 6. Run it

```powershell
python -m scripts.phase7_demo          # agent investigates issue #42

# optional: run the MCP server itself (waits for a client - that's normal)
python -m mcp_server.github_mcp_server
```

To use it from Claude Desktop, add to its MCP config:
```json
{ "mcpServers": { "github-issue-solver": {
    "command": "d:\\archit\\Github_issue\\.venv\\Scripts\\python.exe",
    "args": ["-m", "mcp_server.github_mcp_server"],
    "cwd": "d:\\archit\\Github_issue" } } }
```

## 7. Interview questions you can now answer

- **Q: What is MCP and why does it matter?**
  An open standard (JSON-RPC over stdio/HTTP) for connecting AI apps to tools, resources
  and prompts. It turns N×M custom integrations into N+M: write a tool server once, any
  MCP client can use it.
- **Q: What can an MCP server expose?**
  Tools (actions), Resources (readable data), Prompts (templates) — discoverable at runtime.
- **Q: MCP vs plain function/tool calling?**
  Tool calling is the model's ability to request a function. MCP is the transport/standard
  for *where those tools live* and how clients discover them across apps and processes.
- **Q (the one that catches people out): Does your agent actually USE MCP, or just expose it?**
  Both. I built the server AND an MCP client (`app/tools/mcp_client.py`); the agent
  launches the server over stdio, discovers tools at runtime via `ListToolsRequest`, and
  invokes them via `CallToolRequest`. Exposing a server alone would not make the agent an
  MCP consumer — that's a distinction worth being precise about.
- **Q: What does "runtime discovery" buy you?**
  The client hard-codes nothing. Add a tool to the server and existing clients can use it
  immediately — no redeploy or code change on the client side.
- **Q: Did MCP add latency? How did you handle it?**
  Yes — an extra process hop and serialization. I kept in-process tools on the latency-
  critical path and exposed the same functions over MCP for interoperability.
- **Q: How do you keep an agent with real-world tools safe?**
  Whitelist tools, mock mode for development, cap steps, truncate outputs, validate args,
  and require a PR (human review) rather than direct pushes to main.

✅ Phase 7 done when the agent reads issue #42 and pinpoints `auth.py` by itself.
