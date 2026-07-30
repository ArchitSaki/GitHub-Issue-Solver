# SETUP.md — Phase 1: Get the environment running

> Goal of this phase: a clean Python environment with all tools installed, plus
> a local free LLM (Ollama) ready to answer. No code logic yet — just foundations.

---

## Why each piece exists

| Thing | Why we need it | Analogy |
|-------|----------------|---------|
| **Virtual environment (venv)** | Keeps THIS project's packages separate from other Python projects, so versions never clash. | A separate toolbox per project. |
| **requirements.txt** | A shopping list of packages so anyone can recreate the exact setup with one command. | A recipe's ingredient list. |
| **.env file** | Holds settings/secrets OUTSIDE the code, so we never hard-code them. | Settings menu, not source code. |
| **config.py** | Reads the .env once and shares it everywhere. | The one receptionist who knows all the settings. |
| **Groq** | A very fast cloud LLM API (free tier) for the "thinking". Chosen for LOW LATENCY. | A rented super-fast brain. |
| **FastEmbed** | Runs the embedding model locally (free) because Groq has no embeddings. | A small local translator that turns text into numbers. |

---

## Step-by-step commands (Windows PowerShell)

```powershell
# 1) Go to the project folder
cd d:\archit\Github_issue

# 2) Create a virtual environment (isolated toolbox). We use Python 3.12.
py -3.12 -m venv .venv

# 3) Activate it (your prompt will now show "(.venv)")
.\.venv\Scripts\Activate.ps1
#    If PowerShell blocks the script, run this ONCE then retry activation:
#    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 4) Upgrade pip and install all our packages
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5) Confirm settings load correctly
python -m app.config
```

You should see your settings printed (provider = ollama, github_mode = mock, etc.).

---

## Get your free Groq API key (our fast cloud LLM)

1. Go to https://console.groq.com and sign up (free).
2. Open https://console.groq.com/keys and click **Create API Key**.
3. Copy the key and paste it into your `.env` file:

```
GROQ_API_KEY=gsk_your_key_here
```

That's it — no local model download for reasoning. Groq is cloud + free-tier.

> The embedding model (FastEmbed, ~90 MB) downloads automatically the first time
> RAG runs in Phase 5. It runs locally and stays free.

### Two Groq model choices (set in `.env` as `GROQ_MODEL`)
| Model | When to use |
|-------|-------------|
| `llama-3.3-70b-versatile` | Default. Smarter — better at reading code & planning fixes. |
| `llama-3.1-8b-instant`    | Fastest + cheapest. Use when you want the lowest latency. |

---

## What we created this phase

```
Github_issue/
├── CLAUDE.md            # instructions/memory (Phase 0)
├── docs/
│   ├── ARCHITECTURE.md  # big picture (Phase 0)
│   └── SETUP.md         # this file
├── requirements.txt     # package shopping list
├── .env.example         # settings template (commit this)
├── .env                 # your real settings (do NOT commit)
└── app/
    ├── __init__.py      # marks "app" as a package
    └── config.py        # loads settings from .env
```

## Interview points from Phase 1

- **"Why a virtual environment?"** → Dependency isolation & reproducibility; avoids
  version conflicts between projects.
- **"Why keep config in .env?"** → Separates secrets/config from code (12-factor app
  principle); lets you change environments without changing code; keeps secrets out of git.
- **"Why Pydantic settings?"** → Type-safe, validated config with defaults, loaded from
  the environment automatically.

✅ When `python -m app.config` prints your settings (with provider = groq) and your
`GROQ_API_KEY` is filled in `.env`, Phase 1 is done. We'll test a live Groq call in Phase 2.
