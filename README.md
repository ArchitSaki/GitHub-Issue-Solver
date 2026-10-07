# 🤖 AI GitHub Issue Solver

An **autonomous AI-powered GitHub Issue Solver** that analyzes GitHub issues, investigates the underlying codebase, identifies potential root causes, implements fixes, and creates a Pull Request — reducing the manual effort required to resolve software issues.

The project combines **LLMs, LangGraph, MCP, GitHub APIs, and agentic workflows** to simulate an AI software engineer working on real-world GitHub issues.

---

## 🚀 Overview

Software development teams spend significant time investigating GitHub issues, understanding unfamiliar codebases, identifying root causes, implementing fixes, and preparing Pull Requests.

This project explores:

> **Can an AI agent autonomously take a GitHub issue from problem description → code investigation → solution → Pull Request?**

The GitHub Issue Solver automates this workflow using an agentic architecture.

### Workflow

```text
GitHub Issue
     │
     ▼
┌─────────────────────┐
│   Issue Analysis    │
│ Understand problem  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Repository Analysis │
│ Explore codebase    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Root Cause        │
│    Analysis         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Solution Planning │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Code Modification │
│ Implement the fix   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Validation / Review │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Pull Request     │
└─────────────────────┘
```

---

## ✨ Key Features

### 🔍 1. GitHub Issue Understanding

The agent retrieves and analyzes GitHub issues to understand:

* Problem description
* Expected behavior
* Actual behavior
* Error messages
* Relevant issue context
* Additional comments and information

---

### 🧠 2. Autonomous Codebase Investigation

Instead of relying only on the issue description, the agent investigates the repository to locate relevant code.

It can:

* Explore repository structure
* Search for relevant files
* Read source code
* Identify dependencies between components
* Trace the execution flow
* Locate potentially problematic code

---

### 🧩 3. Root Cause Analysis

The agent attempts to determine **why the issue is occurring**, rather than simply generating a possible patch.

The workflow separates:

```text
Issue
  ↓
Evidence Gathering
  ↓
Code Analysis
  ↓
Hypothesis
  ↓
Root Cause
```

This helps reduce the chance of making unrelated or superficial code changes.

---

### 📝 4. AI-Powered Solution Planning

Before modifying the repository, the agent creates a solution plan describing:

* Files that need modification
* Changes required
* Expected behavior
* Potential side effects
* Validation strategy

This provides an intermediate reasoning step between diagnosis and implementation.

---

### 💻 5. Automated Code Modification

After identifying the root cause, the agent can implement the required changes in the repository.

The objective is to generate **targeted modifications** rather than unnecessarily changing unrelated parts of the codebase.

---

### 🧪 6. Validation

The generated changes can be reviewed and validated before being submitted.

Validation may include:

* Running tests
* Checking modified files
* Reviewing the generated diff
* Verifying the intended behavior

---

### 🔀 7. Pull Request Generation

Once the solution is ready, the agent can create a GitHub Pull Request containing:

* Problem summary
* Root cause
* Implemented solution
* Modified files
* Validation information

This allows the final output of the agent to fit naturally into an existing software development workflow.

---

# 🏗️ Architecture

The system is built around an **agentic state-machine architecture**.

```text
                    ┌─────────────────┐
                    │  GitHub Issue   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Issue Analyzer  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Repository      │
                    │ Investigation   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Root Cause      │
                    │ Analysis        │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Solution        │
                    │ Planner         │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Code            │
                    │ Implementation  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Validation      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Pull Request    │
                    └─────────────────┘
```

---

# 🧠 LangGraph Workflow

The agent workflow is orchestrated using **LangGraph**.

LangGraph is used to represent the software-engineering workflow as a collection of states and transitions.

A simplified workflow looks like:

```text
START
  │
  ▼
Fetch Issue
  │
  ▼
Analyze Issue
  │
  ▼
Inspect Repository
  │
  ▼
Find Relevant Code
  │
  ▼
Analyze Root Cause
  │
  ▼
Generate Solution
  │
  ▼
Implement Changes
  │
  ▼
Run Validation
  │
  ├──── Failure ────► Re-analyze / Fix
  │
  ▼
Create Pull Request
  │
  ▼
END
```

This state-based approach makes it possible to introduce feedback loops when an implementation or validation step fails.

---

# 🔌 MCP Integration

The project uses **Model Context Protocol (MCP)** to provide the AI agent with structured access to development tools.

Instead of giving the LLM unrestricted access to the environment, tools can be exposed through an MCP-based interface.

Examples of capabilities include:

```text
GitHub
 ├── Get issue
 ├── Read repository files
 ├── Search code
 ├── Create branch
 ├── Commit changes
 └── Create Pull Request
```

This allows the LLM to interact with external development resources through defined tools.

---

# 🛠️ Tech Stack

| Technology               | Purpose                               |
| ------------------------ | ------------------------------------- |
| **Python**               | Core application                      |
| **LangGraph**            | Agent workflow orchestration          |
| **LLM**                  | Reasoning, analysis & code generation |
| **MCP**                  | Tool integration                      |
| **GitHub API**           | Repository & issue interaction        |
| **Git**                  | Version control                       |
| **GitHub Pull Requests** | Automated code contribution           |

---

# 📂 Project Structure

```text
github-issue-solver/
│
├── app/
│   ├── agents/
│   │   ├── issue_analyzer.py
│   │   ├── code_analyzer.py
│   │   ├── solution_planner.py
│   │   └── code_agent.py
│   │
│   ├── graph/
│   │   └── workflow.py
│   │
│   ├── tools/
│   │   ├── github_tools.py
│   │   └── repository_tools.py
│   │
│   └── main.py
│
├── prompts/
│   └── ...
│
├── tests/
│   └── ...
│
├── requirements.txt
├── .env.example
└── README.md
```

> The exact structure may vary depending on the current implementation.

---

# ⚙️ How It Works

## 1. Issue Selection

The system receives a GitHub issue as the initial input.

```text
Repository
     +
Issue Number
     ↓
AI GitHub Issue Solver
```

---

## 2. Issue Analysis

The agent first extracts the important information from the issue.

For example:

```text
Problem:
API returns incorrect response when...

Expected:
API should return...

Observed:
API returns...

Relevant Context:
...
```

---

## 3. Repository Investigation

The agent searches through the repository to find code related to the issue.

It may investigate:

```text
Repository
   │
   ├── Routes
   ├── Services
   ├── Models
   ├── Utilities
   └── Tests
```

The goal is to identify the files and functions most likely responsible for the observed behavior.

---

## 4. Root Cause Analysis

The agent combines:

* Issue information
* Repository structure
* Source code
* Error messages
* Relevant dependencies

to formulate a root-cause hypothesis.

---

## 5. Solution Generation

The agent generates a solution plan before modifying the repository.

Example:

```text
1. Modify authentication middleware
2. Update token validation logic
3. Handle expired tokens
4. Add regression test
```

---

## 6. Implementation

The agent applies the proposed changes to the repository.

The changes are kept isolated so that they can be reviewed before merging.

---

## 7. Validation

The system checks whether the changes behave as expected.

```text
Code Changes
     ↓
Run Tests
     ↓
   Pass?
   /   \
 Yes    No
  │      │
  │      └──► Re-analysis
  │
  ▼
Create PR
```

---

## 8. Pull Request

After successful validation, the system prepares a Pull Request containing the implementation and relevant context.

---

# 🔐 Environment Variables

Create a `.env` file:

```env
GITHUB_TOKEN=your_github_token
GITHUB_REPOSITORY=owner/repository
LLM_API_KEY=your_api_key
```

Do **not** commit your `.env` file or API keys to GitHub.

Add it to `.gitignore`:

```text
.env
__pycache__/
.venv/
```

---

# 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/<repository-name>.git

cd <repository-name>
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the environment

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create:

```text
.env
```

and add the required credentials.

### 6. Run the application

```bash
python main.py
```

---

# 🎯 Example Use Case

Suppose a repository contains the issue:

```text
Issue #142

Login API returns 500 when an expired JWT token is provided.
```

Instead of manually:

```text
Read issue
   ↓
Search repository
   ↓
Find authentication code
   ↓
Debug
   ↓
Implement fix
   ↓
Run tests
   ↓
Create PR
```

the AI Issue Solver attempts to automate the workflow:

```text
Issue #142
    ↓
AI Analysis
    ↓
Repository Search
    ↓
Root Cause Identification
    ↓
Fix Generation
    ↓
Validation
    ↓
Pull Request
```

---

# 📊 Project Goals

The primary goals of this project are to explore:

* Autonomous software engineering
* AI-powered debugging
* Agentic workflows
* LLM-based code analysis
* Tool-using AI agents
* GitHub automation
* MCP-based tool integration
* Human-in-the-loop software development

---

# 🔮 Future Improvements

Potential improvements include:

* [ ] Better repository-level code understanding
* [ ] Automated test generation
* [ ] Improved root-cause verification
* [ ] Multi-agent architecture
* [ ] Better handling of large repositories
* [ ] RAG-based code retrieval
* [ ] Automated PR review
* [ ] CI/CD integration
* [ ] Human approval checkpoints
* [ ] Improved failure recovery
* [ ] Observability and agent tracing
* [ ] Evaluation benchmarks for generated fixes

---

# ⚠️ Limitations

AI-generated code should **not be blindly merged into production**.

The system can make incorrect assumptions about:

* Repository architecture
* Intended application behavior
* Dependencies
* Edge cases
* Existing design patterns

Therefore, human review and automated testing remain important before merging generated Pull Requests.

---

# 📚 What I Learned

Building this project helped me understand how AI agents can be integrated into real software-engineering workflows rather than being used only as chat interfaces.

Some of the key concepts explored were:

**LLMs → Tool Calling → MCP → LangGraph → Code Analysis → Autonomous Workflows → GitHub Automation**

The project also highlighted an important challenge in agentic coding:

> Writing code is only one part of solving a software issue. Understanding the problem, navigating the codebase, validating assumptions, and verifying the solution are equally important.

---

# 🤝 Contributing

Contributions, suggestions, and improvements are welcome.

If you find a bug or have an idea for improving the agent:

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a Pull Request

---

# ⭐ Support

If you find this project interesting, consider giving the repository a ⭐.

Feedback and suggestions are always welcome!

---

## 👨‍💻 Author

**Archit Saki**

AI/ML Engineer | Generative AI | AI Agents | MLOps

Interested in building **autonomous AI systems and production-ready ML/GenAI applications**.

---

## 📌 Project Status

🟢 **Active Development**

The project is continuously being improved with new agent capabilities, better codebase understanding, and more reliable autonomous software-engineering workflows.
