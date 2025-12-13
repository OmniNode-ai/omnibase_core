"""
Action Payload Model

Action payload with rich metadata for tool-as-a-service execution.
Wraps a ModelNodeAction with execution parameters and context.
"""

from typing import Any
from uuid import UUID

from pydantic import Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_node_action import ModelNodeAction
from .model_onex_base_state import ModelOnexInputState


class ModelActionPayload(ModelOnexInputState):
    """
    Action payload with rich metadata for tool-as-a-service execution.

    Wraps a ModelNodeAction with execution parameters and context.
    Used for MCP/GraphQL action invocation and service composition.

    Inherits from ModelOnexInputState to get standard traceability fields
    (correlation_id, event_id, timestamp, etc.) for execution tracking.
    """

    action: ModelNodeAction = Field(default=..., description="The action to execute")
    parameters: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Action execution parameters with strong typing",
    )
    execution_context: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Execution context and environment metadata",
    )

    # Execution tracking (in addition to base correlation_id)
    parent_correlation_id: UUID | None = Field(
        default=None,
        description="Parent action correlation ID for chaining",
    )
    execution_chain: list[str] = Field(
        default_factory=list,
        description="Execution chain for action composition tracking",
    )

    # Service composition with strong typing
    target_service: str | None = Field(
        default=None,
        description="Target service for action execution",
    )
    routing_metadata: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Service routing and load balancing metadata",
    )
    trust_level: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Trust score for action execution (0.0-1.0)",
    )

    # Tool-as-a-Service metadata with strong typing
    service_metadata: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Service discovery and composition metadata",
    )
    tool_discovery_tags: list[str] = Field(
        default_factory=list,
        description="Tags for tool discovery and categorization",
    )

    def add_to_execution_chain(self, action_name: str) -> None:
        """Add action to execution chain for composition tracking."""
        self.execution_chain.append(action_name)

    def create_child_payload(
        self,
        child_action: ModelNodeAction,
        **kwargs: Any,
    ) -> "ModelActionPayload":
        """Create child payload for action composition."""
        return ModelActionPayload(
            action=child_action,
            parent_correlation_id=self.correlation_id,
            execution_chain=self.execution_chain.copy(),
            trust_level=min(self.trust_level, kwargs.get("trust_level", 1.0)),
            service_metadata=self.service_metadata.copy(),
            version=self.version,  # Required field from ModelOnexInputState
            **kwargs,
        )
