"""A2A server entrypoint for the Unsplash Photo Explorer agent.

This module initializes the agent, registers it with the A2A framework, and
builds the ASGI application. It follows the 12-factor app pattern: all
configuration is sourced from environment variables.

To run locally:
    uvicorn main:app --reload --port 8001

The agent card is then available at:
    http://localhost:8001/.well-known/agent-card.json
"""

import os
import logging

from dotenv import load_dotenv

from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from gemini_agent import GeminiAgent
from agent_executor import AdkAgentToA2AExecutor

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Load .env file when running locally (no-op in production where env vars are set directly)
load_dotenv()

# The public URL of this agent. Set via environment variable in all deployments.
AGENT_URL = os.environ.get("AGENT_URL", "http://127.0.0.1:8001")

# ---------------------------------------------------------------------------
# Application setup
# Initialized once at module load time for efficiency (avoids cold-start overhead
# in serverless environments where the module is reused across invocations).
# ---------------------------------------------------------------------------

logger.info(f"Starting Unsplash Photo Explorer agent at {AGENT_URL}")

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

logger.info("Agent ready. Agent card: %s/.well-known/agent-card.json", AGENT_URL)
