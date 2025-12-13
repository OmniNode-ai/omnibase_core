"""
Execution Capabilities Model.

Type-safe execution capabilities and constraints for nodes,
replacing Dict[str, Any] with structured configuration.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_delivery_mode import EnumDeliveryMode
from omnibase_core.models.configuration.model_performance_constraints import (
    ModelPerformanceConstraints,
)
from omnibase_core.models.infrastructure.model_duration import ModelDuration

from .model_node_type import ModelNodeType


class ModelExecutionCapabilities(BaseModel):
    """
    Execution capabilities and constraints.

    Provides structured execution capabilities configuration
    replacing Dict[str, Any] with type-safe models.
    """

    supported_node_types: list[ModelNodeType] = Field(
        default=...,
        description="Supported node types",
    )
    supported_delivery_modes: list[EnumDeliveryMode] = Field(
        default=...,
        description="Supported delivery modes",
    )
    max_concurrent_executions: int = Field(
        default=...,
        description="Maximum concurrent executions",
        ge=1,
    )
    timeout: ModelDuration = Field(default=..., description="Default execution timeout")
    performance_constraints: ModelPerformanceConstraints | None = Field(
        default=None,
        description="Performance constraints",
    )
    supports_streaming: bool = Field(
        default=False,
        description="Supports streaming execution",
    )
    supports_batching: bool = Field(
        default=False,
        description="Supports batch execution",
    )
    requires_persistent_storage: bool = Field(
        default=False,
        description="Requires persistent storage",
    )

    def supports_node_type(self, node_type: ModelNodeType) -> bool:
        """Check if a specific node type is supported."""
        return any(
            nt.type_name == node_type.type_name for nt in self.supported_node_types
        )

    def supports_delivery_mode(self, mode: EnumDeliveryMode) -> bool:
        """Check if a specific delivery mode is supported."""
        return mode in self.supported_delivery_modes

    def get_max_timeout_ms(self) -> int:
        """Get maximum timeout in milliseconds."""
        if (
            self.performance_constraints
            and self.performance_constraints.max_execution_time_ms
        ):
            return min(
                self.timeout.total_milliseconds(),
                self.performance_constraints.max_execution_time_ms,
            )
        return self.timeout.total_milliseconds()
