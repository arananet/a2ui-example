"""Agent executor bridging A2A requests to the ADK Gemini agent.

This module provides a custom A2aAgentExecutor implementation that:
1. Uses stable, non-experimental part and event converters.
2. Manually manages sessions to ensure compatibility across ADK versions.
3. Handles A2UI payload extraction and streaming response aggregation.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from a2a.server.agent_execution import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    Artifact,
    Message,
    Role,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from google.adk.runners import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.converters.utils import _get_adk_metadata_key

import gemini_agent
import part_converters

logger = logging.getLogger(__name__)


class AdkAgentToA2AExecutor(A2aAgentExecutor):
    """Custom agent executor that bridges A2A requests to the ADK Gemini agent.

    This executor overrides the standard ADK-to-A2A execution path to provide:
    1. Stable, non-experimental part and event conversions.
    2. Manual session management to bypass SDK version incompatibilities.
    3. Robust A2UI payload handling and extraction.
    """

    def __init__(self):
        """Initializes the executor with a GeminiAgent and standard ADK services."""
        self._agent = gemini_agent.GeminiAgent()
        runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            session_service=InMemorySessionService(),
            artifact_service=InMemoryArtifactService(),
            memory_service=InMemoryMemoryService(),
        )

        super().__init__(runner=runner)

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Entry point for executing an A2A task.

        Args:
            context: The incoming A2A request context and message.
            event_queue: The queue to which status and result events are published.
        """
        await super().execute(context, event_queue)

    async def _handle_request(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Internal handler for processing A2A requests.

        This method manually orchestrates the runner and session preparation to ensure
        stability and allow for custom part conversion logic.
        """
        runner = await self._resolve_runner()
        run_args = part_converters.convert_a2a_request_to_adk_run_args(context)

        # --- SESSION PREPARATION ---
        # We prepare the session manually to avoid an AttributeError related to
        # 'session_id' in some versions of the ADK A2aAgentExecutor.
        session_id = run_args['session_id']
        user_id = run_args['user_id']
        session = await runner.session_service.get_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id,
        )
        if session is None:
            session = await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id=user_id,
                state={},
                session_id=session_id,
            )
            run_args['session_id'] = session.id

        # Initialize invocation context for the runner
        invocation_context = runner._new_invocation_context(
            session=session,
            new_message=run_args['new_message'],
            run_config=run_args['run_config'],
        )

        # Signal that work has started
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                status=TaskStatus(
                    state=TaskState.working,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ),
                context_id=context.context_id,
                final=False,
                metadata={
                    _get_adk_metadata_key('app_name'): runner.app_name,
                    _get_adk_metadata_key('user_id'): run_args['user_id'],
                    _get_adk_metadata_key('session_id'): run_args['session_id'],
                },
            )
        )

        # Aggregator to track the final state across streamed events
        task_result_aggregator = part_converters.TaskResultAggregator()

        # Process ADK events from the runner
        async for adk_event in runner.run_async(**run_args):
            for a2a_event in part_converters.convert_event_to_a2a_events(
                adk_event, invocation_context, context.task_id, context.context_id
            ):
                task_result_aggregator.process_event(a2a_event)
                await event_queue.enqueue_event(a2a_event)

        # --- FINALIZATION ---
        if (
            task_result_aggregator.task_state == TaskState.working
            and task_result_aggregator.task_status_message is not None
            and task_result_aggregator.task_status_message.parts
        ):
            # Publish as an artifact update if successful
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    task_id=context.task_id,
                    last_chunk=True,
                    context_id=context.context_id,
                    artifact=Artifact(
                        artifact_id=str(uuid.uuid4()),
                        parts=task_result_aggregator.task_status_message.parts,
                    ),
                )
            )
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    status=TaskStatus(
                        state=TaskState.completed,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ),
                    context_id=context.context_id,
                    final=True,
                )
            )
        else:
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    status=TaskStatus(
                        state=task_result_aggregator.task_state,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        message=task_result_aggregator.task_status_message,
                    ),
                    context_id=context.context_id,
                    final=True,
                )
            )
