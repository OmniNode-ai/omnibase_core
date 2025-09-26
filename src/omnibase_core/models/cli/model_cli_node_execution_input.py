"""
Model for CLI node execution input parameters.

Replaces primitive dict parameters with type-safe Pydantic models
for CLI node execution operations.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_category_filter import EnumCategoryFilter
from omnibase_core.enums.enum_cli_action import EnumCliAction
from omnibase_core.enums.enum_output_format import EnumOutputFormat

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
    category_filter: EnumCategoryFilter | None = Field(
        None,
        description="Filter nodes by category",
    )

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
        default_factory=ModelCliAdvancedParams,
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelCliNodeExecutionInput"]
