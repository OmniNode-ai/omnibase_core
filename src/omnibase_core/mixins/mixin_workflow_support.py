"""
Mixin for Workflow event support in ONEX tools.

Provides Workflow integration capabilities including event emission, correlation tracking,
and Workflow context detection for tools participating in workflows.
"""

import os
import uuid
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.models.core.model_onex_event import ModelOnexEvent

# Note: Event bus uses duck-typing interface, not a formal protocol
# The omnibase_spi ProtocolEventBus is Kafka-based and incompatible with this interface


class MixinDagSupport:
    """
    Mixin providing Workflow event support for ONEX tools.

    Enables tools to participate in event-driven Workflow orchestration by:
    - Detecting Workflow execution context
    - Emitting Workflow completion events
    - Tracking Workflow correlation IDs
    - Supporting both Workflow and non-Workflow execution modes
    """

    def __init__(self, event_bus: Any = None, **kwargs: Any) -> None:
        """Initialize Workflow support mixin."""
        super().__init__(**kwargs)
        self._event_bus = event_bus
        self._dag_correlation_id: str | None = None
        self._workflow_node_id: str | None = None

    def is_dag_enabled(self) -> bool:
        """
        Detect if tool is executing in Workflow context.

        Checks for Workflow environment variables or correlation ID to determine
        if the tool is part of a workflow.

        Returns:
            bool: True if executing in Workflow context, False otherwise
        """
        # Check for Workflow environment variables
        workflow_context = (
            os.environ.get("ONEX_WORKFLOW_EXECUTION", "false").lower() == "true"
        )
        dag_correlation_id = os.environ.get("ONEX_WORKFLOW_CORRELATION_ID")

        # Check for Workflow correlation ID set by scenario runner
        has_correlation_id = (
            dag_correlation_id is not None or self._dag_correlation_id is not None
        )

        return workflow_context or has_correlation_id

    def set_workflow_context(self, correlation_id: UUID, node_id: UUID) -> None:
        """
        Set Workflow execution context for this tool.

        Args:
            correlation_id: workflow correlation ID
            node_id: This tool's node ID within the Workflow
        """
        self._dag_correlation_id = str(correlation_id)
        self._workflow_node_id = str(node_id)

    def emit_dag_completion_event(
        self,
        result: Any,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """
        Emit Workflow completion event for workflow coordination.

        Args:
            result: Tool execution result
            status: Execution status ("success", "failed", "completed")
            error_message: Optional error message for failed executions
        """
        if not self.is_dag_enabled() or not self._event_bus:
            return

        # Get correlation and node IDs
        correlation_id = self._dag_correlation_id or os.environ.get(
            "ONEX_WORKFLOW_CORRELATION_ID",
            str(uuid.uuid4()),
        )
        node_id = self._workflow_node_id or getattr(self, "node_id", "unknown_tool")

        # Map status to enum
        execution_status = self._map_status_to_enum(status)

        # Create event payload
        event_data = {
            "dag_correlation_id": correlation_id,
            "node_id": node_id,
            "execution_status": execution_status.value,
            "result": self._serialize_result(result),
            "timestamp": self._get_current_timestamp(),
        }

        if error_message:
            event_data["error_message"] = error_message

        # Convert IDs to proper types
        correlation_uuid = (
            UUID(correlation_id) if isinstance(correlation_id, str) else correlation_id
        )
        node_uuid = (
            UUID(node_id)
            if isinstance(node_id, str)
            else (node_id if isinstance(node_id, UUID) else UUID(str(node_id)))
        )

        # Create and emit the event
        event = ModelOnexEvent(
            event_type=f"workflow_node_completed:{node_id}",
            data=event_data,
            correlation_id=correlation_uuid,
            node_id=node_uuid,
        )

        try:
            # Wrap in envelope before publishing
            from omnibase_core.models.events.model_event_envelope import (
                ModelEventEnvelope,
            )

            envelope = ModelEventEnvelope.create_broadcast(
                payload=event,
                source_node_id=node_uuid,
                correlation_id=correlation_uuid,
            )

            self._event_bus.publish_async(envelope)
        except Exception as e:
            # Log error but don't fail the tool execution
            self._safe_log_error(f"Failed to emit Workflow completion event: {e}")

    def emit_dag_start_event(self) -> None:
        """Emit Workflow node start event for monitoring and coordination."""
        if not self.is_dag_enabled() or not self._event_bus:
            return

        correlation_id = self._dag_correlation_id or os.environ.get(
            "ONEX_WORKFLOW_CORRELATION_ID",
            str(uuid.uuid4()),
        )
        node_id = self._workflow_node_id or getattr(self, "node_id", "unknown_tool")

        event_data = {
            "dag_correlation_id": correlation_id,
            "node_id": node_id,
            "execution_status": EnumExecutionStatus.RUNNING.value,
            "timestamp": self._get_current_timestamp(),
        }

        # Convert IDs to proper types
        correlation_uuid = (
            UUID(correlation_id) if isinstance(correlation_id, str) else correlation_id
        )
        node_uuid = (
            UUID(node_id)
            if isinstance(node_id, str)
            else (node_id if isinstance(node_id, UUID) else UUID(str(node_id)))
        )

        event = ModelOnexEvent(
            event_type=f"workflow_node_started:{node_id}",
            data=event_data,
            correlation_id=correlation_uuid,
            node_id=node_uuid,
        )

        try:
            # Wrap in envelope before publishing
            from omnibase_core.models.events.model_event_envelope import (
                ModelEventEnvelope,
            )

            envelope = ModelEventEnvelope.create_broadcast(
                payload=event,
                source_node_id=node_uuid,
                correlation_id=correlation_uuid,
            )

            self._event_bus.publish_async(envelope)
        except Exception as e:
            self._safe_log_error(f"Failed to emit Workflow start event: {e}")

    def _map_status_to_enum(self, status: str) -> EnumExecutionStatus:
        """Map string status to execution status enum."""
        status_mapping = {
            "success": EnumExecutionStatus.COMPLETED,
            "completed": EnumExecutionStatus.COMPLETED,
            "failed": EnumExecutionStatus.FAILED,
            "error": EnumExecutionStatus.FAILED,
            "pending": EnumExecutionStatus.PENDING,
            "running": EnumExecutionStatus.RUNNING,
            "cancelled": EnumExecutionStatus.CANCELLED,
            "timeout": EnumExecutionStatus.TIMEOUT,
            "skipped": EnumExecutionStatus.SKIPPED,
        }
        return status_mapping.get(status.lower(), EnumExecutionStatus.COMPLETED)

    def _serialize_result(self, result: Any) -> dict[str, Any]:
        """Serialize tool result for event emission."""
        try:
            if hasattr(result, "model_dump"):
                # Pydantic model
                serialized: dict[str, Any] = result.model_dump()
                return serialized
            if hasattr(result, "__dict__"):
                # Regular object
                return {k: str(v) for k, v in result.__dict__.items()}
            # Simple value
            return {"value": str(result)}
        except (
            Exception
        ):  # fallback-ok: serialization returns error dict, caller handles gracefully
            return {"serialization_error": "Could not serialize result"}

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat() + "Z"

    def _safe_log_error(self, message: str) -> None:
        """Safely log error without failing tool execution."""
        try:
            # Try to use logger if available
            if hasattr(self, "logger_tool") and self.logger_tool:
                self.logger_tool.log(f"[Workflow] {message}")
            else:
                # Fallback to print
                pass
        except Exception:
            # Silent failure - don't disrupt tool execution
            pass
