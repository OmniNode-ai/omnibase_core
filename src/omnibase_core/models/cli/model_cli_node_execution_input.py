"""
Model for CLI node execution input parameters.

Replaces primitive dict parameters with type-safe Pydantic models
for CLI node execution operations.
"""

from typing import Any, ClassVar, TypedDict
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ...enums.enum_cli_action import EnumCliAction
from ...enums.enum_output_format import EnumOutputFormat
from ..data.model_custom_fields import ModelCustomFields


class ModelCliInputDict(TypedDict, total=False):
    """Type definition for CLI input dictionary."""

    action: str
    output_format: str
    verbose: bool
    request_id: UUID
    execution_context: str | None
    target_node: str | None
    category_filter: str | None


class ModelCliNodeExecutionInput(BaseModel):
    """
    Model for CLI node execution input parameters.

    Provides type safety for node execution inputs while maintaining
    flexibility for different node types and their specific requirements.
    """

    # Core execution parameters
    action: EnumCliAction = Field(..., description="Action to perform with the node")
    node_name: str | None = Field(
        None,
        description="Specific node name for targeted operations",
    )

    # Node-specific parameters
    target_node: str | None = Field(
        None,
        description="Target node name for node-info operations",
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
    category_filter: str | None = Field(None, description="Filter nodes by category")

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
    advanced_params: ModelCustomFields[Any] = Field(
        default_factory=lambda: ModelCustomFields[Any](),
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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action": "list_nodes",
                "node_name": None,
                "target_node": None,
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
