"""
Tool Execution Mixin for ONEX Tool Nodes.

Provides standardized handling of tool.execution.request events,
enabling tools to be executed via the event bus in the unified execution model.
"""

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors import ModelOnexError
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
    from omnibase_core.types.type_serializable_value import SerializedDict


class MixinToolExecution:
    """
    Mixin that provides tool execution event handling.

    This mixin should be combined with MixinEventListener to enable
    tools to respond to tool.execution.request events from the CLI
    or other sources.
    """

    # Type hints for methods expected to be provided by the mixed class
    def get_node_name(self) -> str:
        """Get the node name. Must be implemented by the mixed class."""
        raise NotImplementedError(  # stub-ok: abstract mixin method
            "Must be implemented by the mixed class"
        )

    def process(self, input_state: object) -> object:
        """Process the input state. Must be implemented by the mixed class."""
        raise NotImplementedError(  # stub-ok: abstract mixin method
            "Must be implemented by the mixed class"
        )

    def _get_input_state_class(self) -> type | None:
        """Get the input state class for this tool.

        Returns:
            The input state class, or None if the class cannot be determined
            (e.g., when type introspection fails). When None is returned,
            the tool will operate with dict[str, object] parameters instead.

        Note:
            This return type matches the pattern used in MixinEventListener and
            MixinEventBus for consistency across the mixin system.
        """
        raise NotImplementedError(  # stub-ok: abstract mixin method
            "Must be implemented by the mixed class"
        )

    def handle_tool_execution_request_event(
        self, envelope: "ModelEventEnvelope[object]"
    ) -> None:
        """
        Handle tool execution request events.

        This method is automatically called by MixinEventListener when
        a tool.execution.request event is received.
        """
        event = envelope.payload

        emit_log_event(
            LogLevel.INFO,
            "🎯 Received tool execution request",
            {
                "tool_name": self.get_node_name(),
                "correlation_id": getattr(event, "correlation_id", None),
                "requester": (
                    getattr(event, "data", {}).get("caller", "unknown")
                    if getattr(event, "data", None) is not None
                    else "unknown"
                ),
            },
        )

        try:
            # Extract request data
            event_data_raw = getattr(event, "data", None)
            event_data: dict[str, object] = (
                event_data_raw if isinstance(event_data_raw, dict) else {}
            )
            requested_tool = event_data.get("tool_name", "")
            parameters_raw = event_data.get("parameters", [])
            parameters: list[object] = (
                parameters_raw if isinstance(parameters_raw, list) else []
            )

            # Check if this request is for this tool
            if requested_tool != self.get_node_name():
                emit_log_event(
                    LogLevel.DEBUG,
                    f"🙄 Ignoring execution request for different tool: {requested_tool}",
                    {"my_tool": self.get_node_name(), "requested_tool": requested_tool},
                )
                return

            # Convert parameters to input state
            input_state = self._create_input_state_from_parameters(parameters)

            # Execute the tool
            start_time = time.time()
            output_state = self.process(input_state)
            execution_time = time.time() - start_time

            # Publish successful response
            self._publish_execution_response(
                correlation_id=getattr(event, "correlation_id", None),
                success=True,
                result=self._output_state_to_dict(output_state),
                execution_time=execution_time,
                error=None,
            )

        except (ModelOnexError, RuntimeError, TypeError, ValueError) as e:
            emit_log_event(
                LogLevel.ERROR,
                f"❌ Tool execution failed: {e!s}",
                {
                    "tool_name": self.get_node_name(),
                    "correlation_id": getattr(event, "correlation_id", None),
                    "error_type": type(e).__name__,
                },
            )

            # Publish error response
            self._publish_execution_response(
                correlation_id=getattr(event, "correlation_id", None),
                success=False,
                result=None,
                execution_time=0,
                error=str(e),
            )

    def _create_input_state_from_parameters(self, parameters: list[object]) -> object:
        """
        Create input state from execution parameters.

        Override this method to customize parameter conversion for your tool.
        """
        # Get input state class
        input_state_class = self._get_input_state_class()

        # Convert parameter list to dict - values can be any serializable type
        param_dict: dict[str, object] = {}
        for param in parameters:
            if isinstance(param, dict):
                param_dict[param.get("name", "")] = param.get("value")

        # If no input state class is available, return the param dict directly
        if input_state_class is None:
            emit_log_event(
                LogLevel.DEBUG,
                "No input state class found, using dict[str, object]",
                {"tool_name": self.get_node_name()},
            )
            return param_dict

        # Try to create typed input state
        try:
            # Add any required fields that might be missing
            if hasattr(input_state_class, "model_fields"):
                for field_name, field_info in input_state_class.model_fields.items():
                    if field_name not in param_dict and field_info.is_required:
                        # Set reasonable defaults for common fields
                        if field_name == "action":
                            param_dict["action"] = "execute"
                        elif field_name == "dry_run":
                            param_dict["dry_run"] = False

            return input_state_class(**param_dict)

        except (
            Exception
        ) as e:  # fallback-ok: resilient input parsing, fallback to dict with logging
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to create typed input state, using dict[str, object]: {e!s}",
                {"tool_name": self.get_node_name()},
            )
            # Fallback to dict[str, object] if typed creation fails
            return param_dict

    def _output_state_to_dict(self, output_state: object) -> "SerializedDict":
        """
        Convert output state to dictionary for response.

        Override this method to customize output conversion for your tool.
        """
        from omnibase_core.types.type_serializable_value import SerializedDict

        if hasattr(output_state, "model_dump"):
            # Pydantic model
            result: SerializedDict = output_state.model_dump()
            return result
        if hasattr(output_state, "__dict__"):
            # Regular object - cast to SerializedDict
            obj_dict: SerializedDict = output_state.__dict__
            return obj_dict
        if isinstance(output_state, dict):
            # Already a dict
            return output_state
        # Fallback
        return {"result": str(output_state)}

    def _publish_execution_response(
        self,
        correlation_id: UUID | None,
        success: bool,
        result: "SerializedDict | None",
        execution_time: float,
        error: str | None,
    ) -> None:
        """Publish tool execution response event."""
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

        if not hasattr(self, "event_bus") or not self.event_bus:
            emit_log_event(
                LogLevel.WARNING,
                "⚠️ No event bus available to publish response",
                {"tool_name": self.get_node_name()},
            )
            return

        # Create response event
        # Convert node_id to proper type
        node_id_uuid = (
            self.get_node_id()
            if hasattr(self, "get_node_id")
            else (
                UUID(self.get_node_name())
                if len(self.get_node_name()) == 36
                else uuid4()
            )
        )

        # Use ModelSemVer for default version instead of string literal
        default_version = ModelSemVer(major=1, minor=0, patch=0)
        response_event = ModelOnexEvent(
            event_type="tool.execution.response",
            node_id=node_id_uuid,
            correlation_id=correlation_id,
            timestamp=datetime.fromtimestamp(time.time(), tz=UTC),
            data={  # type: ignore[arg-type]  # Event data field accepts dict for tool execution response; validated at runtime
                "tool_name": self.get_node_name(),
                "success": success,
                "result": result,
                "execution_time": execution_time,
                "error": error,
                "tool_version": getattr(self, "version", str(default_version)),
            },
            metadata=None,
        )

        # Wrap in envelope and publish
        envelope = ModelEventEnvelope.create_broadcast(
            payload=response_event,
            source_node_id=node_id_uuid,
            correlation_id=correlation_id,
        )

        success = self.event_bus.publish(envelope)

        if success:
            emit_log_event(
                LogLevel.INFO,
                "✅ Published tool execution response",
                {
                    "tool_name": self.get_node_name(),
                    "correlation_id": correlation_id,
                    "success": success,
                },
            )
        else:
            emit_log_event(
                LogLevel.ERROR,
                "❌ Failed to publish tool execution response",
                {
                    "tool_name": self.get_node_name(),
                    "correlation_id": correlation_id,
                },
            )

    def get_execution_event_patterns(self) -> list[str]:
        """
        Get event patterns for tool execution.

        This is used by MixinEventListener to subscribe to the right events.
        """
        return [
            "tool.execution.request",  # Listen for execution requests
            f"tool.execution.request.{self.get_node_name()}",  # Tool-specific requests
        ]
