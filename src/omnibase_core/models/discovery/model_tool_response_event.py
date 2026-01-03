# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-07-05T12:00:00.000000'
# description: Tool response event model for persistent service communication
# entrypoint: python://model_tool_response_event
# hash: auto-generated
# last_modified_at: '2025-07-05T12:00:00.000000'
# lifecycle: active
# meta_type: model
# metadata_version: 0.1.0
# name: model_tool_response_event.py
# namespace: python://omnibase.model.discovery.model_tool_response_event
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: auto-generated
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Tool Response Event Model

Event sent in response to a TOOL_INVOCATION event after tool execution completes.
Contains the result of the tool execution or error information if execution failed.
"""

from typing import Any
from uuid import UUID

from pydantic import Field

from omnibase_core.constants.constants_event_types import TOOL_RESPONSE
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.discovery.model_outputmetadata import ModelOutputMetadata
from omnibase_core.models.discovery.model_resource_usage import ModelResourceUsage
from omnibase_core.types.type_serializable_value import SerializedDict
from omnibase_core.types.typed_dict_tool_performance_summary import (
    TypedDictToolPerformanceSummary,
)


class ModelToolResponseEvent(ModelOnexEvent):
    """
    Event sent in response to a TOOL_INVOCATION event.

    This event contains the result of tool execution or error information
    if the execution failed. It includes performance metrics and execution
    metadata for monitoring and debugging.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=TOOL_RESPONSE,
        description="Event type identifier",
    )

    # Response correlation
    correlation_id: UUID = Field(
        default=...,
        description="Correlation ID matching the original TOOL_INVOCATION request",
    )

    # Source node identification
    source_node_id: UUID = Field(
        default=..., description="Node ID that executed the tool"
    )
    source_node_name: str = Field(
        default=...,
        description="Name of the node that executed the tool",
    )

    # Tool execution details
    tool_name: str = Field(
        default=..., description="Name of the tool that was executed"
    )
    action: str = Field(default=..., description="Action that was performed")

    # Execution result
    success: bool = Field(
        default=..., description="Whether the tool execution was successful"
    )
    result: SerializedDict | None = Field(
        default=None,
        description="Tool execution result data (if successful)",
    )
    error: str | None = Field(
        default=None,
        description="Error message (if execution failed)",
    )
    error_code: str | None = Field(
        default=None,
        description="Specific error code for programmatic handling",
    )

    # Performance metrics
    execution_time_ms: int = Field(
        default=...,
        description="Total execution time in milliseconds",
        ge=0,
    )
    queue_time_ms: int | None = Field(
        default=None,
        description="Time spent in queue before execution (if applicable)",
        ge=0,
    )

    # Execution metadata
    execution_priority: str = Field(
        default="normal",
        description="Priority level at which the tool was executed",
    )
    execution_mode: str = Field(
        default="synchronous",
        description="Execution mode (synchronous, asynchronous)",
    )

    # Response routing
    target_node_id: UUID = Field(
        default=...,
        description="Node ID where response should be delivered",
    )
    requester_id: UUID = Field(
        default=...,
        description="Original requester identifier for response handling",
    )

    # Optional detailed information
    output_metadata: ModelOutputMetadata = Field(
        default_factory=ModelOutputMetadata,
        description="Additional metadata about the execution",
    )
    resource_usage: ModelResourceUsage | None = Field(
        default=None,
        description="Resource usage during execution (CPU, memory, etc.)",
    )

    @classmethod
    def create_success_response(
        cls,
        correlation_id: UUID,
        source_node_id: UUID,
        source_node_name: str,
        tool_name: str,
        action: str,
        result: SerializedDict,
        execution_time_ms: int,
        target_node_id: str | UUID,
        requester_id: str | UUID,
        execution_priority: str = "normal",
        **kwargs: Any,
    ) -> "ModelToolResponseEvent":
        """
        Factory method for creating successful tool response events.

        Args:
            correlation_id: Correlation ID from original request
            source_node_id: Node that executed the tool
            source_node_name: Name of the executing node
            tool_name: Tool that was executed
            action: Action that was performed
            result: Execution result data
            execution_time_ms: Total execution time
            target_node_id: Node to deliver response to
            requester_id: Original requester
            execution_priority: Execution priority
            **kwargs: Additional fields

        Returns:
            ModelToolResponseEvent for successful execution
        """
        # Convert IDs to UUID if string
        target_uuid = (
            UUID(target_node_id) if isinstance(target_node_id, str) else target_node_id
        )
        requester_uuid = (
            UUID(requester_id) if isinstance(requester_id, str) else requester_id
        )

        return cls(
            node_id=source_node_id,
            correlation_id=correlation_id,
            source_node_id=source_node_id,
            source_node_name=source_node_name,
            tool_name=tool_name,
            action=action,
            success=True,
            result=result,
            execution_time_ms=execution_time_ms,
            target_node_id=target_uuid,
            requester_id=requester_uuid,
            execution_priority=execution_priority,
            execution_mode="synchronous",
            **kwargs,
        )

    @classmethod
    def create_error_response(
        cls,
        correlation_id: UUID,
        source_node_id: UUID,
        source_node_name: str,
        tool_name: str,
        action: str,
        error: str,
        error_code: str,
        execution_time_ms: int,
        target_node_id: str | UUID,
        requester_id: str | UUID,
        execution_priority: str = "normal",
        **kwargs: Any,
    ) -> "ModelToolResponseEvent":
        """
        Factory method for creating error tool response events.

        Args:
            correlation_id: Correlation ID from original request
            source_node_id: Node that attempted execution
            source_node_name: Name of the executing node
            tool_name: Tool that was attempted
            action: Action that was attempted
            error: Error message
            error_code: Specific error code
            execution_time_ms: Time spent before failure
            target_node_id: Node to deliver response to
            requester_id: Original requester
            execution_priority: Execution priority
            **kwargs: Additional fields

        Returns:
            ModelToolResponseEvent for failed execution
        """
        # Convert IDs to UUID if string
        target_uuid = (
            UUID(target_node_id) if isinstance(target_node_id, str) else target_node_id
        )
        requester_uuid = (
            UUID(requester_id) if isinstance(requester_id, str) else requester_id
        )

        return cls(
            node_id=source_node_id,
            correlation_id=correlation_id,
            source_node_id=source_node_id,
            source_node_name=source_node_name,
            tool_name=tool_name,
            action=action,
            success=False,
            error=error,
            error_code=error_code,
            execution_time_ms=execution_time_ms,
            target_node_id=target_uuid,
            requester_id=requester_uuid,
            execution_priority=execution_priority,
            execution_mode="synchronous",
            **kwargs,
        )

    @classmethod
    def create_timeout_response(
        cls,
        correlation_id: UUID,
        source_node_id: UUID,
        source_node_name: str,
        tool_name: str,
        action: str,
        timeout_ms: int,
        target_node_id: str | UUID,
        requester_id: str | UUID,
        **kwargs: Any,
    ) -> "ModelToolResponseEvent":
        """
        Factory method for creating timeout response events.

        Args:
            correlation_id: Correlation ID from original request
            source_node_id: Node that timed out
            source_node_name: Name of the executing node
            tool_name: Tool that timed out
            action: Action that timed out
            timeout_ms: Timeout duration
            target_node_id: Node to deliver response to
            requester_id: Original requester
            **kwargs: Additional fields

        Returns:
            ModelToolResponseEvent for timeout
        """
        # Convert IDs to UUID if string
        target_uuid = (
            UUID(target_node_id) if isinstance(target_node_id, str) else target_node_id
        )
        requester_uuid = (
            UUID(requester_id) if isinstance(requester_id, str) else requester_id
        )

        return cls(
            node_id=source_node_id,
            correlation_id=correlation_id,
            source_node_id=source_node_id,
            source_node_name=source_node_name,
            tool_name=tool_name,
            action=action,
            success=False,
            error=f"Tool execution timed out after {timeout_ms}ms",
            error_code="TOOL_EXECUTION_TIMEOUT",
            execution_time_ms=timeout_ms,
            target_node_id=target_uuid,
            requester_id=requester_uuid,
            execution_priority="normal",
            execution_mode="synchronous",
            **kwargs,
        )

    def is_successful(self) -> bool:
        """Check if the tool execution was successful."""
        return self.success

    def has_result_data(self) -> bool:
        """Check if response contains result data."""
        return self.success and self.result is not None

    def get_routing_key(self) -> str:
        """Get the routing key for response delivery."""
        return f"response.{self.requester_id}.{self.correlation_id}"

    def get_performance_summary(self) -> TypedDictToolPerformanceSummary:
        """Get a summary of performance metrics."""
        summary: TypedDictToolPerformanceSummary = {
            "execution_time_ms": self.execution_time_ms,
            "priority": self.execution_priority,
            "mode": self.execution_mode,
        }

        if self.queue_time_ms is not None:
            summary["queue_time_ms"] = self.queue_time_ms
            summary["total_time_ms"] = self.execution_time_ms + self.queue_time_ms

        if self.resource_usage:
            summary["resource_usage"] = self.resource_usage

        return summary
