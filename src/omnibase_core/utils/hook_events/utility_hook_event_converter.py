"""Hook event conversion utility.

Converts between different hook event models while maintaining
strong typing throughout the pipeline.
"""

from omnibase_core.model.hook_events.model_claude_code_post_execution_hook_input import (
    ModelClaudeCodePostExecutionHookInput,
)
from omnibase_core.model.hook_events.model_claude_code_pre_execution_hook_input import (
    ModelClaudeCodePreExecutionHookInput,
)
from omnibase_core.model.hook_events.model_onex_hook_event import ModelOnexHookEvent
from omnibase_core.model.hook_events.model_tool_post_execution_event import (
    ModelToolPostExecutionEvent,
)
from omnibase_core.model.hook_events.model_tool_pre_execution_event import (
    ModelToolPreExecutionEvent,
)


class UtilityHookEventConverter:
    """Utility for converting between hook event models."""

    @staticmethod
    def pre_execution_input_to_tool_event(
        hook_input: ModelClaudeCodePreExecutionHookInput,
        session_id_fallback: str = "unknown",
    ) -> ModelToolPreExecutionEvent:
        """Convert Claude Code input to tool execution event.

        Args:
            hook_input: Validated input from Claude Code
            session_id_fallback: Fallback session ID if none provided

        Returns:
            ModelToolPreExecutionEvent for processing
        """
        # Convert tool_input dict to JSON string if present
        parameters_json = None
        if hook_input.tool_input:
            parameters_json = hook_input.tool_input

        return ModelToolPreExecutionEvent(
            tool_name=hook_input.tool_name,
            session_id=hook_input.session_id or session_id_fallback,
            parameters_json=parameters_json,
            claude_message=hook_input.claude_message,
            hook_version="1.0.0",
        )

    @staticmethod
    def post_execution_input_to_tool_event(
        hook_input: ModelClaudeCodePostExecutionHookInput,
        session_id_fallback: str = "unknown",
    ) -> ModelToolPostExecutionEvent:
        """Convert Claude Code post-execution input to tool event.

        Args:
            hook_input: Validated input from Claude Code
            session_id_fallback: Fallback session ID if none provided

        Returns:
            ModelToolPostExecutionEvent for processing
        """
        # Extract result data from tool response
        result = None
        success = True
        error_message = None

        if hook_input.tool_response:
            raw_result = (
                hook_input.tool_response.result or hook_input.tool_response.output
            )
            if isinstance(raw_result, dict | list):
                import json as _json

                result = _json.dumps(raw_result)
            elif raw_result is not None:
                result = str(raw_result)

            # Only default to True when success is None
            success = (
                True
                if hook_input.tool_response.success is None
                else hook_input.tool_response.success
            )

            if hook_input.tool_response.error:
                error_message = hook_input.tool_response.error.message

        return ModelToolPostExecutionEvent(
            tool_name=hook_input.tool_name,
            session_id=hook_input.session_id or session_id_fallback,
            result=result,
            success=success,
            duration_ms=(
                0 if hook_input.duration_ms is None else hook_input.duration_ms
            ),
            error_message=error_message,
            claude_message=hook_input.claude_message,
            hook_version="1.0.0",
        )

    @staticmethod
    def pre_execution_tool_event_to_onex_event(
        tool_event: ModelToolPreExecutionEvent,
        topic: str | None = None,
        working_directory: str | None = None,
    ) -> ModelOnexHookEvent:
        """Convert pre-execution tool event to ONEX hook event.

        Args:
            tool_event: Pre-execution tool event
            topic: Kafka topic for the event
            working_directory: Working directory context

        Returns:
            ModelOnexHookEvent for dashboard and Kafka
        """
        return ModelOnexHookEvent(
            event_type=tool_event.event_type,
            tool_name=tool_event.tool_name,
            session_id=tool_event.session_id,
            conversation_id=tool_event.conversation_id,
            timestamp=tool_event.timestamp,
            hook_version=tool_event.hook_version,
            parameters_json=tool_event.parameters_json,
            claude_message=tool_event.claude_message,
            topic=topic,
            working_directory=working_directory,
        )

    @staticmethod
    def post_execution_tool_event_to_onex_event(
        tool_event: ModelToolPostExecutionEvent,
        topic: str | None = None,
        working_directory: str | None = None,
    ) -> ModelOnexHookEvent:
        """Convert post-execution tool event to ONEX hook event.

        Args:
            tool_event: Post-execution tool event
            topic: Kafka topic for the event
            working_directory: Working directory context

        Returns:
            ModelOnexHookEvent for dashboard and Kafka
        """
        # Convert error message to proper error model if present
        error = None
        if tool_event.error_message:
            from omnibase_core.core.core_error_codes import CoreErrorCode
            from omnibase_core.model.core.model_onex_error import ModelOnexError

            error = ModelOnexError(
                message=tool_event.error_message,
                error_code=CoreErrorCode.OPERATION_FAILED,
            )

        return ModelOnexHookEvent(
            event_type=tool_event.event_type,
            tool_name=tool_event.tool_name,
            session_id=tool_event.session_id,
            conversation_id=tool_event.conversation_id,
            timestamp=tool_event.timestamp,
            hook_version=tool_event.hook_version,
            claude_message=tool_event.claude_message,
            result=tool_event.result,
            success=tool_event.success,
            duration_ms=tool_event.duration_ms,
            error=error,
            topic=topic,
            working_directory=working_directory,
        )
