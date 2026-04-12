# A2UI Unsplash Photo Explorer

An enterprise-grade example of an **Agent-to-User Interface (A2UI)** agent built with [Google's Agent Development Kit (ADK)](https://google.github.io/adk-docs/) and Gemini 2.5 Flash. Users interact with the agent in natural language; the agent queries the [Unsplash API](https://unsplash.com/developers) and renders results as a dynamic, interactive photo gallery UI.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        A2A Client                           │
│                  (e.g., A2UI-capable UI)                    │
└───────────────────────┬─────────────────────────────────────┘
                        │ JSON-RPC over HTTP (A2A Protocol)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    A2A Server (FastAPI)                      │
│                       main.py                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              AdkAgentToA2AExecutor                  │    │
│  │               agent_executor.py                     │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │                   GeminiAgent                        │    │
│  │                 gemini_agent.py                      │    │
│  │                                                      │    │
│  │   Tools:  search_photos()  suggest_random_topic()   │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │              Part Converters                         │    │
│  │              part_converters.py                      │    │
│  │   A2A ↔ GenAI type translation + A2UI extraction    │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼ HTTPS
┌─────────────────────────────────────────────────────────────┐
│                   Unsplash API                              │
│          https://api.unsplash.com/search/photos             │
└─────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

| File | Responsibility |
|------|---------------|
| `main.py` | ASGI entrypoint — initializes agent, builds A2A application |
| `gemini_agent.py` | Agent class, Unsplash tool definitions, agent card |
| `prompt_builder.py` | System prompt, A2UI photo gallery template, theming rules |
| `a2ui_schema.py` | A2UI JSON Schema — defines all valid component structures |
| `part_converters.py` | Stable A2A ↔ GenAI type conversions, A2UI payload extraction |
| `agent_executor.py` | ADK-to-A2A execution bridge with session management |

---

## Tech Stack

- **AI**: [Google ADK](https://google.github.io/adk-docs/) + Gemini 2.5 Flash
- **Agent Protocol**: [A2A (Agent-to-Agent)](https://google.github.io/A2A/)
- **UI Protocol**: A2UI (Agent-to-User Interface)
- **Web Framework**: FastAPI / Starlette / Uvicorn
- **Photos API**: [Unsplash API](https://unsplash.com/documentation)
- **HTTP Client**: [HTTPX](https://www.python-httpx.org/)
- **Config**: python-dotenv (12-factor app pattern)

---

## Prerequisites

- Python 3.11+
- A Google Cloud project with Vertex AI API enabled
- An [Unsplash developer account](https://unsplash.com/developers) with an app registered

---

## Setup

### 1. Clone and enter the project

```bash
git clone https://github.com/arananet/a2ui-example.git
cd a2ui-example/version-2
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env` with your real credentials:

```env
# Google ADK / Gemini
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
MODEL=gemini-2.5-flash
AGENT_URL=http://127.0.0.1:8001

# Unsplash API
UNSPLASH_ACCESS_KEY=your_unsplash_access_key_here
```

> **Security**: `.env` is gitignored and must never be committed. Only `.env.example` (with placeholder values) is tracked in version control.

### 5. Authenticate with Google Cloud

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

---

## Running the Agent

```bash
cd version-2
uvicorn main:app --reload --port 8001
```

The server starts at `http://localhost:8001`.

---

## Verifying the Agent

### Check the Agent Card

```bash
curl http://localhost:8001/.well-known/agent-card.json | python3 -m json.tool
```

### Send a photo search request

Uses the A2A v0.3 `message/send` method:

```bash
curl -X POST http://localhost:8001/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Find me photos of misty mountain peaks"}],
        "messageId": "msg-001"
      }
    }
  }'
```

### Try a random topic suggestion

```bash
curl -X POST http://localhost:8001/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Surprise me with something beautiful"}],
        "messageId": "msg-002"
      }
    }
  }'
```

### Stream a response

Uses the A2A v0.3 `message/stream` method:

```bash
curl -X POST http://localhost:8001/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "3",
    "method": "message/stream",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Find me urban architecture photos"}],
        "messageId": "msg-003"
      }
    }
  }'
```

### Verify no secrets are in source

```bash
grep -r "Client-ID\|UNSPLASH_ACCESS_KEY=" version-2/*.py  # Should return nothing
```

---

## A2UI Photo Gallery Layout

The agent renders search results as a structured A2UI surface:

```
┌────────────────────────────────────────────┐
│  Unsplash Photo Explorer          [Title]  │
│  "mountain landscape"             [Query]  │
│  1,500 photos found    Page 1 of 167       │
├─────────────┬─────────────┬───────────────┤
│  [Photo 1]  │  [Photo 2]  │  [Photo 3]   │
│  by Jane S. │  by John D. │  by Alex M.  │
│  Description│  Description│  Description │
│  [View ↗]   │  [View ↗]   │  [View ↗]    │
├─────────────┴─────────────┴───────────────┤
│  [Photo 4]  │  [Photo 5]  │  [Photo 6]   │
│  ...        │  ...        │  ...         │
├─────────────┴─────────────┴───────────────┤
│         [← Previous]   [Next →]           │
└────────────────────────────────────────────┘
```

---

## Dynamic Theming

The agent selects a primary color based on the search topic:

| Topic Category | Color | Hex |
|----------------|-------|-----|
| Nature / Landscape / Forest | Teal | `#00897B` |
| Architecture / City / Urban | Indigo | `#3949AB` |
| Food / Drink / Cuisine | Amber | `#F57C00` |
| Art / Abstract / Creative | Purple | `#8E24AA` |
| Sport / Fitness / Action | Red | `#E53935` |
| People / Portrait / Culture | Blue Grey | `#546E7A` |
| Travel / Road / Journey | Teal | `#00897B` |
| Technology / Minimal | Cyan | `#00838F` |
| Default | Deep Blue | `#1565C0` |

---

## Agent Skills

| Skill | Example Prompts |
|-------|----------------|
| **Photo Search** | "Find me photos of Tokyo at night" |
| **Pagination** | "Show me page 2 of ocean photos" |
| **Random Topic** | "Surprise me", "Inspire me", "Something random" |
| **Orientation** | "Show portrait photos of people in markets" |

---

## Deploying to Railway

[Railway](https://railway.app) is the recommended deployment target. The repo includes
all required configuration files.

### 1. Create a GCP Service Account

Railway cannot use `gcloud auth`. Create a service account key for production:

```bash
# Create the service account
gcloud iam service-accounts create a2ui-photo-explorer \
  --project YOUR_PROJECT_ID \
  --display-name="A2UI Photo Explorer"

# Grant Vertex AI access
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:a2ui-photo-explorer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Export the key (keep this file secret — never commit it)
gcloud iam service-accounts keys create sa-key.json \
  --iam-account=a2ui-photo-explorer@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 2. Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and initialise
railway login
railway init        # link to a new or existing project
railway up          # deploy
```

Or connect via the Railway dashboard → **New Project → Deploy from GitHub repo**.

### 3. Set Environment Variables

In the Railway dashboard go to your service → **Variables** and add:

| Variable | Value |
|----------|-------|
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | e.g. `us-central1` |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Full contents of `sa-key.json` (one line) |
| `UNSPLASH_ACCESS_KEY` | Your Unsplash Access Key |
| `MODEL` | `gemini-2.5-flash` |
| `AGENT_URL` | Your Railway public URL (set after first deploy) |

> `PORT` is injected automatically by Railway — do not set it.

### 4. Update AGENT_URL

After the first deploy, Railway assigns a public URL (e.g. `https://yourapp.up.railway.app`).
Update the `AGENT_URL` variable in Railway to this URL and redeploy.

### 5. Verify

```bash
# Check the agent card (A2A v0.3 manifest)
curl https://yourapp.up.railway.app/.well-known/agent-card.json | python3 -m json.tool

# Send a test message (A2A v0.3 message/send)
curl -X POST https://yourapp.up.railway.app/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"Find photos of mountain lakes"}],"messageId":"test-001"}}}'
```

### Deployment File Reference

| File | Purpose |
|------|---------|
| `railway.toml` | Railway build/deploy config (repo root) |
| `Procfile` | Start command when root dir is the repo root |
| `requirements.txt` | Root-level pip requirements (forwards to `version-2/`) |
| `version-2/Procfile` | Start command when Railway root dir = `version-2/` |
| `version-2/nixpacks.toml` | Nixpacks build phases (Python 3.11, pip install) |

---

## Unsplash Attribution

Per the [Unsplash API Guidelines](https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines), all photos must attribute the photographer. This agent includes photographer name and profile link in every photo card rendered via A2UI.

Photos are provided by the [Unsplash](https://unsplash.com) community of photographers.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

## Developer

**Eduardo Arana**
