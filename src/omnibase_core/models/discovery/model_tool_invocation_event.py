from typing import Any

"\nTool Invocation Event Model\n\nEvent sent to invoke a tool on a specific node through the persistent service pattern.\nEnables distributed tool execution through event-driven routing.\n"
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from pydantic import Field

from omnibase_core.constants import (
    TIMEOUT_DEFAULT_MS,
    TIMEOUT_LONG_MS,
    TIMEOUT_MIN_MS,
)
from omnibase_core.constants.constants_event_types import TOOL_INVOCATION
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.discovery.model_toolparameters import ModelToolParameters


class ModelToolInvocationEvent(ModelOnexEvent):
    """
    Event sent to invoke a tool on a specific node.

    This event enables distributed tool execution through the persistent service
    pattern. The target node receives this event, executes the tool, and responds
    with a TOOL_RESPONSE event.
    """

    event_type: str = Field(
        default=TOOL_INVOCATION, description="Event type identifier"
    )
    target_node_id: UUID = Field(
        default=...,
        description="Unique identifier of the target node that should execute the tool",
    )
    target_node_name: str = Field(
        default=..., description="Name of the target node (e.g., 'node_generator')"
    )
    tool_name: str = Field(
        default=..., description="Name of the tool to invoke (e.g., 'generate_node')"
    )
    action: str = Field(
        default=...,
        description="Action to perform with the tool (e.g., 'health_check')",
    )
    parameters: ModelToolParameters = Field(
        default_factory=ModelToolParameters,
        description="Parameters to pass to the tool execution",
    )
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique ID for matching responses to this invocation",
    )
    timeout_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        description="Tool execution timeout in milliseconds",
        ge=TIMEOUT_MIN_MS,
        le=TIMEOUT_LONG_MS,
    )
    priority: str = Field(
        default="normal", description="Execution priority (low, normal, high, urgent)"
    )
    async_execution: bool = Field(
        default=False, description="Whether to execute asynchronously (fire-and-forget)"
    )
    requester_id: UUID = Field(
        default=...,
        description="Identifier of the requesting service",
    )
    requester_node_id: UUID = Field(
        default=..., description="Node ID of the requester for response routing"
    )
    routing_hints: dict[str, str | int | float | bool] = Field(
        default_factory=dict, description="Optional hints for routing optimization"
    )

    @classmethod
    def create_tool_invocation(
        cls,
        target_node_id: UUID,
        target_node_name: str,
        tool_name: str,
        action: str,
        requester_id: UUID,
        requester_node_id: UUID,
        parameters: ModelToolParameters | None = None,
        timeout_ms: int = TIMEOUT_DEFAULT_MS,
        priority: str = "normal",
        **kwargs: Any,
    ) -> "ModelToolInvocationEvent":
        """
        Factory method for creating tool invocation events.

        Args:
            target_node_id: Target node identifier
            target_node_name: Target node name
            tool_name: Tool to invoke
            action: Action to perform
            requester_id: Requesting service identifier
            requester_node_id: Requester node ID
            parameters: Tool parameters
            timeout_ms: Execution timeout
            priority: Execution priority
            **kwargs: Additional fields

        Returns:
            ModelToolInvocationEvent instance
        """
        return cls(
            node_id=requester_node_id,
            target_node_id=target_node_id,
            target_node_name=target_node_name,
            tool_name=tool_name,
            action=action,
            requester_id=requester_id,
            requester_node_id=requester_node_id,
            parameters=parameters or ModelToolParameters(),
            timeout_ms=timeout_ms,
            priority=priority,
            **kwargs,
        )

    @classmethod
    def create_mcp_tool_invocation(
        cls,
        target_node_name: str,
        tool_name: str,
        action: str,
        parameters: ModelToolParameters | None = None,
        timeout_ms: int = 10000,
        **kwargs: Any,
    ) -> "ModelToolInvocationEvent":
        """
        Factory method for MCP server tool invocations.

        Args:
            target_node_name: Target node name
            tool_name: Tool to invoke
            action: Action to perform
            parameters: Tool parameters
            timeout_ms: Execution timeout
            **kwargs: Additional fields

        Returns:
            ModelToolInvocationEvent for MCP usage
        """
        mcp_uuid = uuid5(NAMESPACE_DNS, "mcp_server")
        return cls(
            node_id=mcp_uuid,
            target_node_id=uuid4(),
            target_node_name=target_node_name,
            tool_name=tool_name,
            action=action,
            requester_id=uuid4(),
            requester_node_id=mcp_uuid,
            parameters=parameters or ModelToolParameters(),
            timeout_ms=timeout_ms,
            priority="high",
            **kwargs,
        )

    @classmethod
    def create_cli_tool_invocation(
        cls,
        target_node_name: str,
        tool_name: str,
        action: str,
        parameters: ModelToolParameters | None = None,
        timeout_ms: int = 60000,
        **kwargs: Any,
    ) -> "ModelToolInvocationEvent":
        """
        Factory method for CLI tool invocations.

        Args:
            target_node_name: Target node name
            tool_name: Tool to invoke
            action: Action to perform
            parameters: Tool parameters
            timeout_ms: Execution timeout (longer for CLI)
            **kwargs: Additional fields

        Returns:
            ModelToolInvocationEvent for CLI usage
        """
        cli_uuid = uuid5(NAMESPACE_DNS, "cli_client")
        return cls(
            node_id=cli_uuid,
            target_node_id=uuid4(),
            target_node_name=target_node_name,
            tool_name=tool_name,
            action=action,
            requester_id=uuid4(),
            requester_node_id=cli_uuid,
            parameters=parameters or ModelToolParameters(),
            timeout_ms=timeout_ms,
            priority="normal",
            **kwargs,
        )

    def get_routing_key(self) -> str:
        """Get the routing key for event bus routing."""
        return f"tool.{self.target_node_name}.{self.tool_name}"

    def is_high_priority(self) -> bool:
        """Check if this is a high priority invocation."""
        return self.priority in ["high", "urgent"]

    def get_expected_response_time_ms(self) -> int:
        """Get the expected response time based on priority and timeout."""
        if self.priority == "urgent":
            return min(self.timeout_ms // 4, 5000)
        if self.priority == "high":
            return min(self.timeout_ms // 2, 10000)
        return self.timeout_ms
