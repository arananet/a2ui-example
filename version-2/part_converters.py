"""Conversion utilities for bridging Google GenAI and A2UI/ADK types.

This module provides stable, non-experimental implementations of part and event converters
to handle the translation between Google GenAI SDK types and A2UI/ADK messaging types.
It specifically addresses A2UI JSON payload extraction and tool call metadata handling.
"""

from typing import Optional, List, Any, Dict, Tuple
import logging
import json
import pydantic
import uuid
from datetime import datetime, timezone

from a2a import types as a2a_types
from a2a.types import TaskStatus, TaskState, TaskStatusUpdateEvent, Message, Role
from a2a.server.events import Event as A2AEvent
from google.genai import types as genai_types
from google.adk.a2a.converters import part_converter
from google.adk.runners import RunConfig

logger = logging.getLogger(__name__)

# --- CONSTANTS ---
# Metadata keys and types (copied from ADK to avoid experimental warnings)
ADK_METADATA_KEY_PREFIX = "adk_"
A2A_DATA_PART_METADATA_TYPE_KEY = 'type'
A2A_DATA_PART_METADATA_TYPE_FUNCTION_CALL = 'function_call'
A2A_DATA_PART_METADATA_TYPE_FUNCTION_RESPONSE = 'function_response'
A2A_DATA_PART_METADATA_TYPE_CODE_EXECUTION_RESULT = 'code_execution_result'
A2A_DATA_PART_METADATA_TYPE_EXECUTABLE_CODE = 'executable_code'

# --- HELPERS ---

def _get_adk_metadata_key(key: str) -> str:
    """Returns the ADK-prefixed metadata key."""
    return f"{ADK_METADATA_KEY_PREFIX}{key}"

def is_a2ui_part(a2a_part: a2a_types.Part) -> bool:
    """Checks if an A2A part contains an A2UI payload.

    Args:
        a2a_part: The A2A part to inspect.

    Returns:
        True if the part is a DataPart containing A2UI rendering or data update keys.
    """
    if hasattr(a2a_part, 'root') and isinstance(a2a_part.root, a2a_types.DataPart):
        data = a2a_part.root.data
        if isinstance(data, dict):
            # Check for common A2UI keys
            return any(key in data for key in ["beginRendering", "surfaceUpdate", "dataModelUpdate", "deleteSurface"])
        if isinstance(data, list) and len(data) > 0:
            # Check first item of a list (A2UI often sends a list of messages)
            first = data[0]
            if isinstance(first, dict):
                return any(key in first for key in ["beginRendering", "surfaceUpdate", "dataModelUpdate", "deleteSurface"])
    return False

def _extract_a2ui_json(text: str) -> Tuple[str, Optional[str]]:
    """Extracts the A2UI JSON payload from a text string using the standard delimiter.

    Args:
        text: The raw text string containing conversational text and optionally A2UI JSON.

    Returns:
        A tuple of (conversational_text, ui_json_string).
    """
    if "---a2ui_JSON---" in text:
        parts = text.split("---a2ui_JSON---", 1)
        conversational_text = parts[0].strip()
        ui_json = parts[1].strip().lstrip("```json").rstrip("```").strip()
        return conversational_text, ui_json
    return text, None

# --- CONVERTERS ---

def convert_a2a_part_to_genai_part(
    a2a_part: a2a_types.Part,
) -> Optional[genai_types.Part]:
    """Converts an A2A Part to a GenAI Part, serializing A2UI parts as JSON.

    Args:
        a2a_part: The A2A part to convert.

    Returns:
        The corresponding GenAI part, or None if conversion fails.
    """
    if is_a2ui_part(a2a_part):
        return genai_types.Part(text=a2a_part.model_dump_json())

    # Custom stable conversion for non-A2UI parts
    part = a2a_part.root
    if isinstance(part, a2a_types.TextPart):
        return genai_types.Part(text=part.text)

    if isinstance(part, a2a_types.DataPart):
        if part.metadata and _get_adk_metadata_key(A2A_DATA_PART_METADATA_TYPE_KEY) in part.metadata:
            meta_type = part.metadata[_get_adk_metadata_key(A2A_DATA_PART_METADATA_TYPE_KEY)]
            if meta_type == A2A_DATA_PART_METADATA_TYPE_FUNCTION_CALL:
                return genai_types.Part(function_call=genai_types.FunctionCall.model_validate(part.data, by_alias=True))
            if meta_type == A2A_DATA_PART_METADATA_TYPE_FUNCTION_RESPONSE:
                return genai_types.Part(function_response=genai_types.FunctionResponse.model_validate(part.data, by_alias=True))
            if meta_type == A2A_DATA_PART_METADATA_TYPE_CODE_EXECUTION_RESULT:
                return genai_types.Part(code_execution_result=genai_types.CodeExecutionResult.model_validate(part.data, by_alias=True))
            if meta_type == A2A_DATA_PART_METADATA_TYPE_EXECUTABLE_CODE:
                return genai_types.Part(executable_code=genai_types.ExecutableCode.model_validate(part.data, by_alias=True))

        # Default DataPart (including A2UI) as text if not handled above
        return genai_types.Part(text=json.dumps(part.data))

    # Fallback to SDK for other types (FilePart etc.)
    try:
        return part_converter.convert_a2a_part_to_genai_part(a2a_part)
    except Exception as e:
        logger.warning(f"Fallback conversion failed: {e}")
        return None

def convert_genai_part_to_a2a_parts(
    part: genai_types.Part,
) -> List[a2a_types.Part]:
    """Converts a GenAI Part to a LIST of A2A Parts, correctly handling A2UI payloads.

    Args:
        part: The GenAI part to convert.

    Returns:
        A list of A2A parts (typically one text part and zero or more UI/data parts).
    """
    if part.text:
        text_content, ui_json = _extract_a2ui_json(part.text)

        if ui_json:
            logger.debug(f"A2UI JSON found: {ui_json[:100]}...")
            try:
                # Try to parse as an A2A Part (schema-conformant)
                a2a_part = a2a_types.Part.model_validate_json(ui_json)
                if is_a2ui_part(a2a_part):
                    res_parts = []
                    if text_content:
                        res_parts.append(a2a_types.Part(root=a2a_types.TextPart(text=text_content)))
                    res_parts.append(a2a_part)
                    return res_parts
            except (pydantic.ValidationError, json.JSONDecodeError):
                pass

            # Try as raw JSON list/dict (A2UI payload directly)
            try:
                ui_data = json.loads(ui_json)
                res_parts = []
                if text_content:
                    res_parts.append(a2a_types.Part(root=a2a_types.TextPart(text=text_content)))
                res_parts.append(a2a_types.Part(root=a2a_types.DataPart(data=ui_data)))
                return res_parts
            except json.JSONDecodeError:
                logger.warning("Failed to parse A2UI JSON, returning as plain text.")
                return [a2a_types.Part(root=a2a_types.TextPart(text=part.text))]

        # Plain text with no A2UI delimiter
        return [a2a_types.Part(root=a2a_types.TextPart(text=part.text))]

    if part.function_call:
        return [a2a_types.Part(root=a2a_types.DataPart(
            data=part.function_call.model_dump(by_alias=True),
            metadata={_get_adk_metadata_key(A2A_DATA_PART_METADATA_TYPE_KEY): A2A_DATA_PART_METADATA_TYPE_FUNCTION_CALL},
        ))]

    if part.function_response:
        return [a2a_types.Part(root=a2a_types.DataPart(
            data=part.function_response.model_dump(by_alias=True),
            metadata={_get_adk_metadata_key(A2A_DATA_PART_METADATA_TYPE_KEY): A2A_DATA_PART_METADATA_TYPE_FUNCTION_RESPONSE},
        ))]

    if part.inline_data:
        import base64
        return [a2a_types.Part(root=a2a_types.FilePart(
            file=a2a_types.FileWithBytes(
                bytes=base64.b64encode(part.inline_data.data).decode('utf-8'),
                mime_type=part.inline_data.mime_type,
            )
        ))]

    # Fallback for unknown part types
    try:
        converted = part_converter.convert_genai_part_to_a2a_part(part)
        return [converted] if converted else []
    except Exception as e:
        logger.warning(f"Fallback part conversion failed: {e}")
        return []


def convert_event_to_a2a_message(
    event: Any,
    invocation_context: Any,
    role: a2a_types.Role = a2a_types.Role.agent
) -> Optional[a2a_types.Message]:
    """Extracts and converts GenAI parts from an ADK event into an A2A message.

    Args:
        event: The ADK event containing model content.
        invocation_context: The runner's invocation context.
        role: The role (default: agent).

    Returns:
        An A2A Message populated with converted parts, or None if no content found.
    """
    content = getattr(event, 'content', None)
    if not content:
        return None

    parts = getattr(content, 'parts', None)
    if not parts:
        return None

    a2a_parts = []
    for part in parts:
        # Filter out parts that are EXCLUSIVELY thoughts/reasoning
        is_exclusively_thought = False
        if (hasattr(part, 'thought') and part.thought) or (hasattr(part, 'thought_signature') and part.thought_signature):
            if not getattr(part, 'text', None):
                is_exclusively_thought = True

        # Double check model_extra for raw SDK fields
        if not is_exclusively_thought and hasattr(part, 'model_extra') and part.model_extra:
            extras = part.model_extra
            if ('thought' in extras or 'thought_signature' in extras) and not getattr(part, 'text', None):
                is_exclusively_thought = True

        if is_exclusively_thought:
            continue

        # Convert and extend the parts list
        try:
            p_list = convert_genai_part_to_a2a_parts(part)
            a2a_parts.extend(p_list)
        except Exception as e:
            logger.error(f"Part conversion failed: {e}")
            pass

    if a2a_parts:
        return a2a_types.Message(message_id=str(uuid.uuid4()), role=role, parts=a2a_parts)
    return None


def convert_event_to_a2a_events(
    event: Any,
    invocation_context: Any,
    task_id: Optional[str] = None,
    context_id: Optional[str] = None,
) -> List[Any]:
    """Converts a single ADK event into a list of A2A events for streaming.

    Args:
        event: The ADK event to convert.
        invocation_context: The active invocation context.
        task_id: The A2A task ID.
        context_id: The A2A context ID.

    Returns:
        A list of A2A events (TaskStatusUpdateEvent, etc.).
    """
    a2a_events = []

    # Handle SDK errors reported in events
    if hasattr(event, 'error_code') and event.error_code:
        a2a_events.append(TaskStatusUpdateEvent(
            task_id=task_id,
            context_id=context_id,
            status=TaskStatus(
                state=TaskState.failed,
                message=Message(
                    role=Role.agent,
                    parts=[a2a_types.Part(root=a2a_types.TextPart(text=f"Error: {event.error_code}"))],
                    message_id=str(uuid.uuid4())
                ),
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            final=True
        ))
        return a2a_events

    # Convert generic message content
    message = convert_event_to_a2a_message(event, invocation_context)
    if message:
        status = TaskStatus(
            state=TaskState.working,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        a2a_events.append(TaskStatusUpdateEvent(
            task_id=task_id,
            context_id=context_id,
            status=status,
            final=False
        ))

    return a2a_events


class TaskResultAggregator:
    """Aggregates TaskStatusUpdateEvents to determine the final state and message.

    This provides a stable version of the logic to avoid experimental SDK warnings.
    """

    def __init__(self):
        self._task_state = TaskState.working
        self._task_status_message = None

    def process_event(self, event: Any):
        if isinstance(event, TaskStatusUpdateEvent):
            if event.status.state == TaskState.failed:
                self._task_state = TaskState.failed
                self._task_status_message = event.status.message
            elif self._task_state == TaskState.working:
                self._task_status_message = event.status.message
            # Ensure state is reported as working during aggregation
            event.status.state = TaskState.working

    @property
    def task_state(self) -> Any:
        return self._task_state

    @property
    def task_status_message(self) -> Optional[Message]:
        return self._task_status_message


def convert_a2a_request_to_adk_run_args(
    request: Any,
) -> dict:
    """Converts an A2A RequestContext into arguments suitable for ADK Runner.run_async.

    Args:
        request: The incoming A2A RequestContext.

    Returns:
        A dictionary of runner arguments {user_id, session_id, new_message, run_config}.
    """
    if not request.message:
        raise ValueError('Request message cannot be None')

    # Default user ID from context
    user_id = f'A2A_USER_{request.context_id}'
    if (request.call_context and request.call_context.user and request.call_context.user.user_name):
        user_id = request.call_context.user.user_name

    return {
        'user_id': user_id,
        'session_id': request.context_id,
        'new_message': genai_types.Content(
            role='user',
            parts=[
                convert_a2a_part_to_genai_part(part)
                for part in request.message.parts
            ],
        ),
        'run_config': RunConfig(),
    }
