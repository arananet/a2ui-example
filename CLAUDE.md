# CLAUDE.md — A2UI Unsplash Photo Explorer

This file provides guidance to Claude Code when working in this repository.
Read it fully before making any changes.

---

## Project Overview

This is an **enterprise-grade A2UI agent** built with Google's Agent Development Kit (ADK)
and Gemini 2.5 Flash. It uses the Unsplash API to search photos and renders results as a
dynamic photo gallery via the **A2UI (Agent-to-User Interface)** protocol over
**A2A (Agent-to-Agent)** transport.

All implementation lives in `version-2/`. The spec that drives this implementation is at
`spec/agent-spec.md`. Always read the spec before making functional changes.

---

## Repository Structure

```
a2ui-example/
├── CLAUDE.md                    ← You are here
├── README.md                    ← End-user documentation
├── .gitignore
├── spec/
│   └── agent-spec.md            ← Canonical specification (source of truth)
└── version-2/
    ├── main.py                  ← ASGI entrypoint
    ├── gemini_agent.py          ← Agent class + Unsplash tool definitions
    ├── prompt_builder.py        ← A2UI UI templates + system prompt builder
    ├── a2ui_schema.py           ← A2UI JSON Schema (component type definitions)
    ├── part_converters.py       ← A2A ↔ GenAI type conversion utilities
    ├── agent_executor.py        ← ADK-to-A2A execution bridge
    ├── requirements.txt         ← Python dependencies
    └── .env.example             ← Environment variable template (no real secrets)
```

---

## Development Principles

### Spec-Driven Development
- **The spec comes first.** Any functional change MUST start with an update to `spec/agent-spec.md`.
- Implementation must trace back to spec requirements (use Req IDs like `REQ-TOOL-001`).
- Do not add features not in the spec without updating the spec first.

### Secrets Management (Non-Negotiable)
- **NEVER hardcode credentials, API keys, or tokens in any file.**
- All secrets are loaded via `os.environ.get(...)` with `python-dotenv` for local dev.
- The only committed secrets-related file is `.env.example` with placeholder values.
- Always verify: `grep -rn "Client-ID [A-Za-z]\|UNSPLASH.*=" version-2/*.py` returns nothing.

### Code Style
- Python 3.11+, type hints throughout.
- Google-style docstrings on all public functions and classes.
- Logging via `logging.getLogger(__name__)` — no `print()` in production code.
- Module-level constants in `UPPER_SNAKE_CASE`.
- No abbreviations in variable names; prefer clarity over brevity.

### A2UI Protocol Rules
- The `---a2ui_JSON---` delimiter separates conversational text from A2UI JSON payload.
- Every photo search result response must emit 3 A2UI messages in order:
  1. `beginRendering` — surface initialization with theme color
  2. `surfaceUpdate` — component tree definition
  3. `dataModelUpdate` — data binding via `valueStruct`
- Never emit A2UI for purely conversational responses.
- All data binding uses `valueStruct` paths (e.g., `/photos/results[]/url`).

### No External Repo References
- Do not reference any external repositories in code, comments, or documentation.
- The architecture is original to this project.

---

## Running Locally

```bash
# 1. Set up environment
cd version-2
cp .env.example .env          # Fill in real credentials
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Authenticate with Google Cloud
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# 3. Start the server
uvicorn main:app --reload --port 8001

# 4. Verify
curl http://localhost:8001/.well-known/agent-card.json
```

---

## Adding or Modifying Tools

1. Update `spec/agent-spec.md` with the new tool's requirement entry.
2. Define the tool function in `version-2/gemini_agent.py` with a complete Google-style docstring.
3. Register it in `GeminiAgent.__init__` tools list.
4. Update the system prompt in `version-2/prompt_builder.py` if UI output changes.
5. Verify no secrets are introduced: `grep -rn "os.environ.get" version-2/gemini_agent.py`.

---

## Modifying the A2UI Schema

`version-2/a2ui_schema.py` contains the canonical A2UI JSON Schema.
Only modify it if the A2UI protocol spec is updated. Changes here affect all component
validation and must be accompanied by updates to the template in `prompt_builder.py`.

---

## Git Workflow

- Branch: `claude/a2ui-google-sdk-example-wt1d5`
- Commit messages follow Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Each commit should be atomic and traceable to a spec requirement.
- Never force-push. Never commit `.env`.

---

## Key Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `UNSPLASH_ACCESS_KEY` | Unsplash API Access Key | Yes |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | Yes |
| `GOOGLE_CLOUD_LOCATION` | GCP region (e.g., `us-central1`) | Yes |
| `MODEL` | Gemini model ID | No (default: `gemini-2.5-flash`) |
| `AGENT_URL` | Public URL of this agent | No (default: `http://127.0.0.1:8001`) |

---

## Developer

Eduardo Arana
