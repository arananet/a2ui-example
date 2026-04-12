"""A2A server entrypoint for the Unsplash Photo Explorer agent.

This module initializes the agent, registers it with the A2A framework, and
builds the ASGI application. It follows the 12-factor app pattern: all
configuration is sourced from environment variables.

Local development:
    uvicorn main:app --reload --port 8001

Railway deployment:
    The platform sets $PORT automatically. Uvicorn is started via Procfile.
    Google Cloud credentials are bootstrapped from GOOGLE_APPLICATION_CREDENTIALS_JSON.

Agent card endpoint:
    GET /.well-known/agent-card.json
"""

import json
import logging
import os
import tempfile

from dotenv import load_dotenv

from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from gemini_agent import GeminiAgent
from agent_executor import AdkAgentToA2AExecutor

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Load .env file when running locally (no-op in production where env vars are set directly)
load_dotenv()


# ---------------------------------------------------------------------------
# Google Cloud credentials bootstrap
#
# Railway (and similar platforms) cannot mount credential files, so this
# agent supports providing the service account JSON as an environment variable.
# If GOOGLE_APPLICATION_CREDENTIALS_JSON is set and
# GOOGLE_APPLICATION_CREDENTIALS is not already pointing to a file, the JSON
# is written to a temporary file and the standard env var is set accordingly.
# ---------------------------------------------------------------------------

def _bootstrap_google_credentials() -> None:
    """Writes inline GCP credentials to a temp file for Railway deployment.

    Railway cannot mount files, so the service account JSON is passed as the
    GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable. This function
    materializes it to a temporary file and sets GOOGLE_APPLICATION_CREDENTIALS
    so that the Google ADK and all Google Cloud client libraries pick it up
    automatically via Application Default Credentials (ADC).

    This is a no-op when GOOGLE_APPLICATION_CREDENTIALS is already set (e.g.,
    local development with gcloud auth application-default login).
    """
    inline_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    already_set = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if inline_json and not already_set:
        try:
            # Validate that the value is parseable JSON before writing
            json.loads(inline_json)
            credentials_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
                prefix="gcp_sa_",
            )
            credentials_file.write(inline_json)
            credentials_file.flush()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file.name
            logger.info(
                "Google credentials bootstrapped from GOOGLE_APPLICATION_CREDENTIALS_JSON "
                "→ %s",
                credentials_file.name,
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(
                "Failed to bootstrap Google credentials: %s. "
                "Ensure GOOGLE_APPLICATION_CREDENTIALS_JSON contains valid JSON.",
                exc,
            )
    elif already_set:
        logger.info("Using existing GOOGLE_APPLICATION_CREDENTIALS: %s", already_set)
    else:
        logger.info(
            "No explicit credentials found. Relying on Application Default Credentials "
            "(e.g., gcloud auth application-default login)."
        )


# ---------------------------------------------------------------------------
# Application setup
#
# Initialized at module load time for efficiency — avoids cold-start overhead
# in serverless/container environments where the module is reused across requests.
# ---------------------------------------------------------------------------

_bootstrap_google_credentials()

AGENT_URL = os.environ.get("AGENT_URL", "http://127.0.0.1:8001")

logger.info("Starting Unsplash Photo Explorer agent at %s", AGENT_URL)

agent = GeminiAgent()
agent_card = agent.create_agent_card(AGENT_URL)

request_handler = DefaultRequestHandler(
    agent_executor=AdkAgentToA2AExecutor(),
    task_store=InMemoryTaskStore(),
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
).build()

logger.info("Agent ready — %s/.well-known/agent-card.json", AGENT_URL)
