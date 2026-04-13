"""A2UI Photo Explorer — Visual Frontend.

A FastAPI application that acts as a visual client for the A2UI photo explorer
agent. It proxies A2A JSON-RPC calls to the backend agent and renders the
A2UI responses (beginRendering + surfaceUpdate + dataModelUpdate) as a rich,
interactive photo gallery web UI.

Environment variables:
    AGENT_URL: URL of the A2A agent backend (default: http://127.0.0.1:8001)
    PORT:      Server port (injected by Railway; default: 8080)
"""

import json
import logging
import os
import uuid
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

AGENT_URL: str = os.environ.get("AGENT_URL", "http://127.0.0.1:8001")

app = FastAPI(
    title="A2UI Photo Explorer — Visual Frontend",
    description="Visual web client for the A2UI Unsplash Photo Explorer agent.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# A2UI PARSING UTILITIES
# ---------------------------------------------------------------------------

A2UI_DELIMITER = "---a2ui_JSON---"


def parse_agent_response(raw_text: str) -> dict[str, Any]:
    """Splits an agent response into a conversational part and parsed A2UI data.

    Args:
        raw_text: The raw text response from the A2A agent, which may contain
                  an A2UI JSON payload after the ``---a2ui_JSON---`` delimiter.

    Returns:
        A dict with keys:
            ``message`` (str): The conversational text portion.
            ``a2ui``    (list | None): Parsed A2UI message list, or None if absent.
            ``error``   (str | None): Parse error description, or None.
    """
    if A2UI_DELIMITER not in raw_text:
        return {"message": raw_text.strip(), "a2ui": None, "error": None}

    parts = raw_text.split(A2UI_DELIMITER, 1)
    conversational_text = parts[0].strip()
    raw_json = parts[1].strip()

    try:
        a2ui_messages = json.loads(raw_json)
        if not isinstance(a2ui_messages, list):
            return {
                "message": conversational_text,
                "a2ui": None,
                "error": "A2UI payload is not a JSON array.",
            }
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse A2UI JSON: %s", exc)
        return {
            "message": conversational_text,
            "a2ui": None,
            "error": f"A2UI JSON parse error: {exc}",
        }

    return {"message": conversational_text, "a2ui": a2ui_messages, "error": None}


def extract_theme(a2ui_messages: list[dict]) -> dict[str, str]:
    """Extracts theme information from the beginRendering A2UI message.

    Args:
        a2ui_messages: Parsed list of A2UI message objects.

    Returns:
        A dict with ``primaryColor`` and ``font`` keys.
    """
    defaults = {"primaryColor": "#1565C0", "font": "Inter"}
    for msg in a2ui_messages:
        if msg.get("type") == "beginRendering":
            styles = msg.get("styles", {})
            return {
                "primaryColor": styles.get("primaryColor", defaults["primaryColor"]),
                "font": styles.get("font", defaults["font"]),
            }
    return defaults


def extract_value_struct(a2ui_messages: list[dict]) -> dict[str, Any]:
    """Extracts the valueStruct data model from the dataModelUpdate A2UI message.

    Args:
        a2ui_messages: Parsed list of A2UI message objects.

    Returns:
        The photos data dict, or an empty dict if not found.
    """
    for msg in a2ui_messages:
        if msg.get("type") == "dataModelUpdate":
            return msg.get("valueStruct", {}).get("photos", {})
    return {}


# ---------------------------------------------------------------------------
# A2A PROXY HELPERS
# ---------------------------------------------------------------------------

async def call_agent(user_message: str, session_id: str) -> str:
    """Sends a message to the A2A agent and returns the text response.

    Args:
        user_message: Natural language message from the user.
        session_id: Session identifier to maintain conversation continuity.

    Returns:
        The agent's text response (may include A2UI payload).

    Raises:
        HTTPException: If the agent call fails or returns an error.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": user_message}],
                "messageId": str(uuid.uuid4()),
            },
            "configuration": {
                "sessionId": session_id,
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(AGENT_URL, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.RequestError as exc:
        logger.error("Agent request failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Agent unreachable: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        logger.error("Agent HTTP error %s: %s", exc.response.status_code, exc.response.text)
        raise HTTPException(
            status_code=502, detail=f"Agent returned {exc.response.status_code}"
        ) from exc

    # Extract text from A2A response envelope
    if "error" in data:
        logger.error("Agent RPC error: %s", data["error"])
        raise HTTPException(status_code=502, detail=str(data["error"]))

    result = data.get("result", {})
    # A2A message/send result wraps in status.message or artifacts
    artifacts = result.get("artifacts", [])
    if artifacts:
        parts = artifacts[0].get("parts", [])
        text_parts = [p.get("text", "") for p in parts if p.get("kind") == "text"]
        return "\n".join(text_parts)

    # Fallback: check status message
    status = result.get("status", {})
    message = status.get("message", {})
    parts = message.get("parts", [])
    text_parts = [p.get("text", "") for p in parts if p.get("kind") == "text"]
    return "\n".join(text_parts) if text_parts else "No response received from agent."


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Serves the main A2UI Photo Explorer web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint for Railway."""
    return JSONResponse({"status": "ok", "agent_url": AGENT_URL})


@app.post("/api/chat")
async def chat(request: Request) -> JSONResponse:
    """Proxies a chat message to the A2A agent and returns structured A2UI data.

    Request body:
        message (str): The user's natural language message.
        session_id (str): Session identifier for conversation continuity.

    Returns:
        JSON with keys: message, a2ui, theme, photos, raw_a2ui, error.
    """
    body = await request.json()
    user_message = body.get("message", "").strip()
    session_id = body.get("session_id") or str(uuid.uuid4())

    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    logger.info("Chat request [session=%s]: %r", session_id, user_message[:80])

    raw_response = await call_agent(user_message, session_id)
    parsed = parse_agent_response(raw_response)

    theme = {}
    photos = {}
    if parsed["a2ui"]:
        theme = extract_theme(parsed["a2ui"])
        photos = extract_value_struct(parsed["a2ui"])

    return JSONResponse({
        "session_id": session_id,
        "message": parsed["message"],
        "a2ui": parsed["a2ui"],
        "theme": theme,
        "photos": photos,
        "raw_a2ui": json.dumps(parsed["a2ui"], indent=2) if parsed["a2ui"] else None,
        "error": parsed["error"],
    })
