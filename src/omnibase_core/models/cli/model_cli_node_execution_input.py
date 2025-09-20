"""
Model for CLI node execution input parameters.

Replaces primitive dict parameters with type-safe Pydantic models
for CLI node execution operations.
"""

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from ..data.model_custom_fields import ModelCustomFields


class ModelCliNodeExecutionInput(BaseModel):
    """
    Model for CLI node execution input parameters.

    Provides type safety for node execution inputs while maintaining
    flexibility for different node types and their specific requirements.
    """

    # Core execution parameters
    action: str = Field(..., description="Action to perform with the node")
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
    output_format: str = Field(
        "default",
        description="Output format preference (default, json, table)",
    )
    verbose: bool = Field(default=False, description="Enable verbose output")

    # Advanced parameters (typed model for safety)
    advanced_params: ModelCustomFields = Field(
        default_factory=lambda: ModelCustomFields(),
        description="Advanced parameters specific to individual nodes",
    )

    # Execution context
    execution_context: str | None = Field(
        None,
        description="Execution context identifier",
    )
    request_id: str | None = Field(
        None,
        description="Request identifier for tracking",
    )

    def to_legacy_dict(self) -> dict[str, Any]:
        """
        Convert to legacy dictionary format for current standards.

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
        if self.node_name:
            base_dict["node_name"] = self.node_name
        if self.target_node:
            base_dict["target_node"] = self.target_node
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
    def from_legacy_dict(cls, data: dict[str, Any]) -> "ModelCliNodeExecutionInput":
        """
        Create instance from legacy dictionary format.

        Args:
            data: Legacy dictionary parameters

        Returns:
            ModelCliNodeExecutionInput instance
        """
        # Extract known fields
        known_fields = {
            "action",
            "node_name",
            "target_node",
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

        # Create ModelCustomFields from the remaining parameters
        advanced_params = ModelCustomFields()
        for key, value in advanced_dict.items():
            advanced_params.set_field(key, value)

        return cls(advanced_params=advanced_params, **base_params)

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
                "execution_context": "cli_main",
                "request_id": "req_123456",
            },
        }
    )
