# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-07-05T12:00:00.000000'
# description: Tool invocation event model for persistent service communication
# entrypoint: python://model_tool_invocation_event
# hash: auto-generated
# last_modified_at: '2025-07-05T12:00:00.000000'
# lifecycle: active
# meta_type: model
# metadata_version: 0.1.0
# name: model_tool_invocation_event.py
# namespace: python://omnibase.model.discovery.model_tool_invocation_event
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
Tool Invocation Event Model

Event sent to invoke a tool on a specific node through the persistent service pattern.
Enables distributed tool execution through event-driven routing.
"""

from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.core.constants.event_types import CoreEventTypes
from omnibase_core.model.core.model_onex_event import ModelOnexEvent
from omnibase_core.model.discovery.model_tool_parameters import ModelToolParameters


class ModelToolInvocationEvent(ModelOnexEvent):
    """
    Event sent to invoke a tool on a specific node.

    This event enables distributed tool execution through the persistent service
    pattern. The target node receives this event, executes the tool, and responds
    with a TOOL_RESPONSE event.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=CoreEventTypes.TOOL_INVOCATION,
        description="Event type identifier",
    )

    # Target node identification
    target_node_id: str = Field(
        ...,
        description="Unique identifier of the target node that should execute the tool",
    )
    target_node_name: str = Field(
        ...,
        description="Name of the target node (e.g., 'node_generator')",
    )

    # Tool execution details
    tool_name: str = Field(
        ...,
        description="Name of the tool to invoke (e.g., 'generate_node')",
    )
    action: str = Field(
        ...,
        description="Action to perform with the tool (e.g., 'health_check')",
    )
    parameters: ModelToolParameters = Field(
        default_factory=ModelToolParameters,
        description="Parameters to pass to the tool execution",
    )

    # Request control
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique ID for matching responses to this invocation",
    )
    timeout_ms: int = Field(
        default=30000,
        description="Tool execution timeout in milliseconds",
        ge=1000,
        le=300000,  # Max 5 minutes
    )

    # Execution options
    priority: str = Field(
        default="normal",
        description="Execution priority (low, normal, high, urgent)",
    )
    async_execution: bool = Field(
        default=False,
        description="Whether to execute asynchronously (fire-and-forget)",
    )

    # Request metadata
    requester_id: str = Field(
        ...,
        description="Identifier of the requesting service (e.g., 'mcp_server', 'cli')",
    )
    requester_node_id: str = Field(
        ...,
        description="Node ID of the requester for response routing",
    )

    # Optional routing hints
    routing_hints: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Optional hints for routing optimization",
    )

    @classmethod
    def create_tool_invocation(
        cls,
        target_node_id: str,
        target_node_name: str,
        tool_name: str,
        action: str,
        requester_id: str,
        requester_node_id: str,
        parameters: ModelToolParameters = None,
        timeout_ms: int = 30000,
        priority: str = "normal",
        **kwargs,
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
        parameters: ModelToolParameters = None,
        timeout_ms: int = 10000,
        **kwargs,
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
        return cls(
            node_id="mcp_server",
            target_node_id=f"{target_node_name}_service",
            target_node_name=target_node_name,
            tool_name=tool_name,
            action=action,
            requester_id="mcp_server",
            requester_node_id="mcp_server",
            parameters=parameters or ModelToolParameters(),
            timeout_ms=timeout_ms,
            priority="high",  # MCP requests are high priority
            **kwargs,
        )

    @classmethod
    def create_cli_tool_invocation(
        cls,
        target_node_name: str,
        tool_name: str,
        action: str,
        parameters: ModelToolParameters = None,
        timeout_ms: int = 60000,
        **kwargs,
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
        return cls(
            node_id="cli_client",
            target_node_id=f"{target_node_name}_service",
            target_node_name=target_node_name,
            tool_name=tool_name,
            action=action,
            requester_id="cli_client",
            requester_node_id="cli_client",
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
