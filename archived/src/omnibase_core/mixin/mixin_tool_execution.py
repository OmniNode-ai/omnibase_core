"""
Tool Execution Mixin for ONEX Tool Nodes.

Provides standardized handling of tool.execution.request events,
enabling tools to be executed via the event bus in the unified execution model.
"""

import time
from typing import Any

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.core.model_onex_event import ModelOnexEvent


class MixinToolExecution:
    """
    Mixin that provides tool execution event handling.

    This mixin should be combined with MixinEventListener to enable
    tools to respond to tool.execution.request events from the CLI
    or other sources.
    """

    def handle_tool_execution_request_event(self, envelope: ModelEventEnvelope) -> None:
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
                "correlation_id": event.correlation_id,
                "requester": event.data.get("caller", "unknown"),
            },
        )

        try:
            # Extract request data
            requested_tool = event.data.get("tool_name", "")
            parameters = event.data.get("parameters", [])
            event.data.get("timeout", 30)

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
                correlation_id=event.correlation_id,
                success=True,
                result=self._output_state_to_dict(output_state),
                execution_time=execution_time,
                error=None,
            )

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"❌ Tool execution failed: {e!s}",
                {
                    "tool_name": self.get_node_name(),
                    "correlation_id": event.correlation_id,
                    "error_type": type(e).__name__,
                },
            )

            # Publish error response
            self._publish_execution_response(
                correlation_id=event.correlation_id,
                success=False,
                result=None,
                execution_time=0,
                error=str(e),
            )

    def _create_input_state_from_parameters(self, parameters: list) -> Any:
        """
        Create input state from execution parameters.

        Override this method to customize parameter conversion for your tool.
        """
        # Get input state class
        input_state_class = self._get_input_state_class()

        # Convert parameter list to dict
        param_dict = {}
        for param in parameters:
            if isinstance(param, dict):
                param_dict[param.get("name", "")] = param.get("value")

        # Try to create input state
        try:
            # Add any required fields that might be missing
            if hasattr(input_state_class, "__fields__"):
                for field_name, field_info in input_state_class.__fields__.items():
                    if field_name not in param_dict and field_info.is_required():
                        # Set reasonable defaults for common fields
                        if field_name == "action":
                            param_dict["action"] = "execute"
                        elif field_name == "dry_run":
                            param_dict["dry_run"] = False

            return input_state_class(**param_dict)

        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"⚠️ Failed to create typed input state, using dict: {e!s}",
                {"tool_name": self.get_node_name()},
            )
            # Fallback to dict if typed creation fails
            return param_dict

    def _output_state_to_dict(self, output_state: Any) -> dict[str, Any]:
        """
        Convert output state to dictionary for response.

        Override this method to customize output conversion for your tool.
        """
        if hasattr(output_state, "model_dump"):
            # Pydantic model
            return output_state.model_dump()
        if hasattr(output_state, "__dict__"):
            # Regular object
            return output_state.__dict__
        if isinstance(output_state, dict):
            # Already a dict
            return output_state
        # Fallback
        return {"result": str(output_state)}

    def _publish_execution_response(
        self,
        correlation_id: str,
        success: bool,
        result: dict[str, Any] | None,
        execution_time: float,
        error: str | None,
    ) -> None:
        """Publish tool execution response event."""
        if not hasattr(self, "event_bus") or not self.event_bus:
            emit_log_event(
                LogLevel.WARNING,
                "⚠️ No event bus available to publish response",
                {"tool_name": self.get_node_name()},
            )
            return

        # Create response event
        response_event = ModelOnexEvent(
            event_type="tool.execution.response",
            node_id=self.get_node_name(),
            correlation_id=correlation_id,
            timestamp=time.time(),
            data={
                "tool_name": self.get_node_name(),
                "success": success,
                "result": result,
                "execution_time": execution_time,
                "error": error,
            },
            metadata={
                "tool_version": getattr(self, "version", "1.0.0"),
            },
        )

        # Wrap in envelope and publish
        envelope = ModelEventEnvelope.create_broadcast(
            payload=response_event,
            source_node_id=self.get_node_name(),
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

    def get_execution_event_patterns(self) -> list:
        """
        Get event patterns for tool execution.

        This is used by MixinEventListener to subscribe to the right events.
        """
        return [
            "tool.execution.request",  # Listen for execution requests
            f"tool.execution.request.{self.get_node_name()}",  # Tool-specific requests
        ]
