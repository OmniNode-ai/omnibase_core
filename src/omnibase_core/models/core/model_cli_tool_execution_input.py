from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_advanced_params import ModelAdvancedParams
from omnibase_core.models.core.model_cli_tool_execution_config import ModelConfig

"""
Model for CLI tool execution input parameters.

Replaces primitive dictionary parameters with type-safe Pydantic models
for CLI tool execution operations.
"""


class ModelCliToolExecutionInput(BaseModel):
    """
    Model for CLI tool execution input parameters.

    Provides type safety for tool execution inputs while maintaining
    flexibility for different tool types and their specific requirements.
    """

    # Core execution parameters
    action: str = Field(default=..., description="Action to perform with the tool")
    tool_name: str | None = Field(
        default=None,
        description="Specific tool name for targeted operations",
    )

    # Tool-specific parameters
    target_tool: str | None = Field(
        default=None,
        description="Target tool name for tool-info operations",
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
        description="Only include healthy tools in results",
    )
    category_filter: str | None = Field(
        default=None, description="Filter tools by category"
    )

    # Performance and timeouts
    timeout_seconds: float | None = Field(
        default=None,
        description="Execution timeout in seconds",
    )

    # Output formatting
    output_format: str = Field(
        default="default",
        description="Output format preference (default, json, table)",
    )
    verbose: bool = Field(default=False, description="Enable verbose output")

    # Advanced parameters (typed model for safety)
    advanced_params: ModelAdvancedParams = Field(
        default_factory=lambda: ModelAdvancedParams(),
        description="Advanced parameters specific to individual tools",
    )

    # Execution context
    execution_context: str | None = Field(
        default=None,
        description="Execution context identifier",
    )
    request_id: UUID | None = Field(
        default=None,
        description="Request identifier for tracking",
    )

    def to_legacy_dict(self) -> dict[str, Any]:
        """
        Convert to legacy dict[str, Any]ionary format for current standards.

        Returns:
            Dictionary representation compatible with existing code
        """
        base_dict = {
            "action": self.action,
            "include_metadata": self.include_metadata,
            "health_filter": self.health_filter,
            "timeout_seconds": self.timeout_seconds,
            "output_format": self.output_format,
            "verbose": self.verbose,
        }

        # Add optional fields if present
        if self.tool_name:
            base_dict["tool_name"] = self.tool_name
        if self.target_tool:
            base_dict["target_tool"] = self.target_tool
        if self.category_filter:
            base_dict["category_filter"] = self.category_filter
        if self.execution_context:
            base_dict["execution_context"] = self.execution_context
        if self.request_id:
            base_dict["request_id"] = self.request_id

        # Merge advanced parameters
        base_dict.update(self.advanced_params.to_dict())

        return base_dict

    @classmethod
    def from_legacy_dict(cls, data: dict[str, Any]) -> "ModelCliToolExecutionInput":
        """
        Create instance from legacy dict[str, Any]ionary format.

        Args:
            data: Legacy dict[str, Any]ionary parameters

        Returns:
            ModelCliToolExecutionInput instance
        """
        # Extract known fields
        known_fields = {
            "action",
            "tool_name",
            "target_tool",
            "include_metadata",
            "include_health_info",
            "health_filter",
            "category_filter",
            "timeout_seconds",
            "output_format",
            "verbose",
            "execution_context",
            "request_id",
        }

        # Separate known from advanced parameters
        base_params = {k: v for k, v in data.items() if k in known_fields}
        advanced_dict = {k: v for k, v in data.items() if k not in known_fields}

        # Create ModelAdvancedParams from the remaining parameters
        advanced_params = ModelAdvancedParams.from_dict(advanced_dict)

        return cls(advanced_params=advanced_params, **base_params)
