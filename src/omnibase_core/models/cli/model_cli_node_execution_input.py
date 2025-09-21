"""
Model for CLI node execution input parameters.

Replaces primitive dict parameters with type-safe Pydantic models
for CLI node execution operations.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ...enums.enum_category_filter import EnumCategoryFilter
from ...enums.enum_cli_action import EnumCliAction
from ...enums.enum_output_format import EnumOutputFormat
from .model_cli_advanced_params import ModelCliAdvancedParams


class ModelCliNodeExecutionInput(BaseModel):
    """
    Model for CLI node execution input parameters.

    Provides type safety for node execution inputs while maintaining
    flexibility for different node types and their specific requirements.
    """

    # Core execution parameters
    action: EnumCliAction = Field(..., description="Action to perform with the node")
    node_id: UUID | None = Field(
        None,
        description="Node UUID for precise identification",
    )
    node_display_name: str | None = Field(
        None,
        description="Node display name for human-readable operations",
    )

    # Node-specific parameters
    target_node_id: UUID | None = Field(
        None,
        description="Target node UUID for precise node-info operations",
    )
    target_node_display_name: str | None = Field(
        None,
        description="Target node display name for node-info operations",
    )

    # Input/output configuration
    include_metadata: bool = Field(
        default=True,
        description="Whether to include detailed metadata in results",
    )
    include_health_info: bool = Field(
        default=True,
        description="Whether to include health information",
    )

    # Filtering and selection
    health_filter: bool = Field(
        default=True,
        description="Only include healthy nodes in results",
    )
    category_filter: EnumCategoryFilter | None = Field(None, description="Filter nodes by category")

    # Performance and timeouts
    timeout_seconds: float | None = Field(
        None,
        description="Execution timeout in seconds",
    )

    # Output formatting
    output_format: EnumOutputFormat = Field(
        EnumOutputFormat.DEFAULT,
        description="Output format preference for results display",
    )
    verbose: bool = Field(default=False, description="Enable verbose output")

    # Advanced parameters (typed model for safety)
    advanced_params: ModelCliAdvancedParams = Field(
        default_factory=lambda: ModelCliAdvancedParams(
            timeout_seconds=None,
            max_retries=None,
            retry_delay_ms=None,
            memory_limit_mb=None,
            cpu_limit_percent=None,
            max_parallel_tasks=None,
            cache_ttl_seconds=None,
        ),
        description="Advanced parameters specific to individual nodes",
    )

    # Execution context
    execution_context: UUID | None = Field(
        None,
        description="Execution context UUID for tracking operations",
    )
    request_id: UUID = Field(
        default_factory=uuid4,
        description="Request UUID for tracking and correlation",
    )

    @property
    def node_name(self) -> str | None:
        """Backward compatibility property for node_name."""
        return self.node_display_name

    @node_name.setter
    def node_name(self, value: str | None) -> None:
        """Backward compatibility setter for node_name."""
        self.node_display_name = value

    @property
    def target_node(self) -> str | None:
        """Backward compatibility property for target_node."""
        return self.target_node_display_name

    @target_node.setter
    def target_node(self, value: str | None) -> None:
        """Backward compatibility setter for target_node."""
        self.target_node_display_name = value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action": "list_nodes",
                "node_id": None,
                "node_display_name": None,
                "target_node_id": None,
                "target_node_display_name": None,
                "include_metadata": True,
                "include_health_info": True,
                "health_filter": True,
                "category_filter": None,
                "timeout_seconds": 30.0,
                "output_format": "default",
                "verbose": False,
                "advanced_params": {},
                "execution_context": "550e8400-e29b-41d4-a716-446655440000",
                "request_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            },
        }
    )


# Export for use
__all__ = ["ModelCliNodeExecutionInput"]
