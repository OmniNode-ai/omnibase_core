"""
Model for CLI node execution input parameters.

Replaces primitive parameters with type-safe Pydantic models
for CLI node execution operations.
"""

from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.decorators import allow_dict_any
from omnibase_core.enums.enum_category_filter import EnumCategoryFilter
from omnibase_core.enums.enum_cli_action import EnumCliAction
from omnibase_core.enums.enum_output_format import EnumOutputFormat
from omnibase_core.types.typed_dict_cli_node_execution_input_serialized import (
    TypedDictCliNodeExecutionInputSerialized,
)

from .model_cli_advanced_params import ModelCliAdvancedParams


class ModelCliNodeExecutionInput(BaseModel):
    """
    Model for CLI node execution input parameters.

    Provides type safety for node execution inputs while maintaining
    flexibility for different node types and their specific requirements.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    # Core execution parameters
    action: EnumCliAction = Field(
        default=..., description="Action to perform with the node"
    )
    node_id: UUID | None = Field(
        default=None,
        description="Node UUID for precise identification",
    )
    node_display_name: str | None = Field(
        default=None,
        description="Node display name for human-readable operations",
    )

    # Node-specific parameters
    target_node_id: UUID | None = Field(
        default=None,
        description="Target node UUID for precise node-info operations",
    )
    target_node_display_name: str | None = Field(
        default=None,
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
        default=None,
        description="Filter nodes by category",
    )

    # Performance and timeouts
    timeout_seconds: float | None = Field(
        default=None,
        description="Execution timeout in seconds",
    )

    # Output formatting
    output_format: EnumOutputFormat = Field(
        default=EnumOutputFormat.TEXT,
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
        default=None,
        description="Execution context UUID for tracking operations",
    )
    request_id: UUID = Field(
        default_factory=uuid4,
        description="Request UUID for tracking and correlation",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=True,
        validate_assignment=True,
        from_attributes=True,
    )

    # Protocol method implementations

    @allow_dict_any
    def serialize(self) -> TypedDictCliNodeExecutionInputSerialized:
        """Serialize to dictionary (Serializable protocol)."""
        return cast(
            TypedDictCliNodeExecutionInputSerialized,
            self.model_dump(exclude_none=False, by_alias=True, mode="json"),
        )

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


# Export for use
__all__ = ["ModelCliNodeExecutionInput"]
