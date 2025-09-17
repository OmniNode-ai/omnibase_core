"""Node infrastructure models for introspection and event bus operations."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_node_capabilities import ModelNodeCapabilities
from omnibase_core.models.core.model_semver import ModelSemVer

# Type variables for generic event bus functionality
InputStateT = TypeVar("InputStateT")
OutputStateT = TypeVar("OutputStateT")


class ModelNodeIntrospectionData(BaseModel):
    """
    Strongly typed container for node introspection data.

    This replaces the loose Dict[str, str | ModelSemVer | List[str] | ...] with
    proper type safety and clear field definitions. Uses the canonical
    ModelNodeCapabilities structure for capabilities data.
    """

    node_name: str = Field(..., description="Node name identifier")
    version: ModelSemVer = Field(..., description="Semantic version of the node")
    capabilities: ModelNodeCapabilities = Field(..., description="Node capabilities")
    tags: list[str] = Field(default_factory=list, description="Discovery tags")
    health_endpoint: str | None = Field(None, description="Health check endpoint")


class ModelMixinEventBus(BaseModel, Generic[InputStateT, OutputStateT]):
    """
    Unified mixin for all event bus operations in ONEX nodes.

    Provides generic event bus functionality with type safety for input and output states.
    This model serves as a base for event-driven node implementations.
    """

    # Configuration
    model_config = {"arbitrary_types_allowed": True}

    # Core event bus properties
    node_id: str = Field(..., description="Unique node identifier")
    event_bus_enabled: bool = Field(
        default=True,
        description="Enable event bus functionality",
    )
    max_event_queue_size: int = Field(
        default=1000,
        description="Maximum event queue size",
    )

    # State management
    current_input_state: InputStateT | None = Field(
        default=None,
        description="Current input state",
    )
    current_output_state: OutputStateT | None = Field(
        default=None,
        description="Current output state",
    )

    # Event processing metrics
    events_processed: int = Field(default=0, description="Total events processed")
    events_failed: int = Field(
        default=0,
        description="Total events that failed processing",
    )

    def reset_metrics(self) -> None:
        """Reset event processing metrics."""
        self.events_processed = 0
        self.events_failed = 0

    def get_success_rate(self) -> float:
        """Calculate event processing success rate."""
        total = self.events_processed + self.events_failed
        if total == 0:
            return 1.0
        return self.events_processed / total
