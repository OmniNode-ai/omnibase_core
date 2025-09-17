"""
CLI Output Data Model

Structured model for CLI command execution output data,
replacing Dict[str, Any] with typed fields.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_custom_fields import ModelCustomFields
from omnibase_core.models.core.model_node_info import ModelNodeInfo
from omnibase_core.models.core.model_node_metadata_info import ModelNodeMetadataInfo


class ModelCliOutputData(BaseModel):
    """
    Structured output data from CLI command execution.

    This model provides typed fields for common CLI output patterns
    while still allowing extensibility through custom fields.
    """

    # Common output fields
    message: str | None = Field(None, description="Human-readable output message")

    status: str | None = Field(None, description="Status indicator")

    # Node-related output
    nodes: list[ModelNodeInfo] | None = Field(
        None,
        description="List of nodes (for discovery/list commands)",
    )

    node_info: ModelNodeInfo | None = Field(
        None,
        description="Single node information",
    )

    node_metadata: ModelNodeMetadataInfo | None = Field(
        None,
        description="Node metadata information",
    )

    # Registry-related output
    registry_count: int | None = Field(
        None,
        description="Number of items in registry",
    )

    registry_status: str | None = Field(
        None,
        description="Registry status information",
    )

    # Validation/test results
    validation_passed: bool | None = Field(
        None,
        description="Whether validation passed",
    )

    test_results: dict[str, bool] | None = Field(
        None,
        description="Test results by test name",
    )

    # Scenario results
    scenario_name: str | None = Field(None, description="Name of executed scenario")

    scenario_status: str | None = Field(
        None,
        description="Scenario execution status",
    )

    # Config/settings output
    config_details: dict[str, Any] | None = Field(
        None,
        description="Configuration values",
    )

    # File operation results
    files_processed: list[str] | None = Field(
        None,
        description="List of processed files",
    )

    files_created: list[str] | None = Field(
        None,
        description="List of created files",
    )

    files_modified: list[str] | None = Field(
        None,
        description="List of modified files",
    )

    # Numeric results
    count: int | None = Field(None, description="Generic count value")

    total: int | None = Field(None, description="Total items")

    processed: int | None = Field(None, description="Items processed")

    failed: int | None = Field(None, description="Items failed")

    skipped: int | None = Field(None, description="Items skipped")

    # Extended fields for complex outputs
    custom_fields: ModelCustomFields | None = Field(
        None,
        description="Extensible custom fields for specific commands",
    )

    # Compatibility field for truly dynamic data
    # This should only be used when the structure is genuinely unknown
    raw_data: dict[str, Any] | None = Field(
        None,
        description="Raw unstructured data (use sparingly)",
    )

    def get_field_value(self, field_name: str, default: Any = None) -> Any:
        """Get a field value by name, checking custom fields if not found."""
        # First check direct fields
        if hasattr(self, field_name):
            value = getattr(self, field_name)
            if value is not None:
                return value

        # Then check custom fields
        if self.custom_fields:
            return self.custom_fields.get_field(field_name, default)

        # Finally check raw data
        if self.raw_data and field_name in self.raw_data:
            return self.raw_data[field_name]

        return default

    def set_field_value(self, field_name: str, value: Any) -> None:
        """Set a field value, using custom fields for non-standard fields."""
        # If it's a known field, set it directly
        if hasattr(self, field_name) and field_name not in [
            "custom_fields",
            "raw_data",
        ]:
            setattr(self, field_name, value)
        else:
            # Otherwise use custom fields
            if not self.custom_fields:
                self.custom_fields = ModelCustomFields()
            self.custom_fields.set_field(field_name, value)

    def to_dict(self, include_none: bool = False) -> dict[str, Any]:
        """Convert to dictionary, optionally including None values."""
        # Use model_dump() as base and filter None values if requested
        data = {}

        # Add all fields, optionally filtering None values
        for field_name, field_value in self.model_dump().items():
            if include_none or field_value is not None:
                data[field_name] = field_value

        # Merge custom fields if present
        if self.custom_fields:
            custom_data = self.custom_fields.to_dict()
            for key, value in custom_data.items():
                if key not in data:  # Don't override standard fields
                    data[key] = value

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelCliOutputData":
        """Create from dictionary, handling unknown fields gracefully."""
        known_fields = set(cls.model_fields.keys())
        standard_data = {}
        custom_data = {}

        for key, value in data.items():
            if key in known_fields:
                standard_data[key] = value
            else:
                custom_data[key] = value

        # Create instance with standard fields
        instance = cls(**standard_data)

        # Add custom fields if any
        if custom_data:
            instance.custom_fields = ModelCustomFields()
            for key, value in custom_data.items():
                instance.custom_fields.set_field(key, value)

        return instance

    @classmethod
    def create_simple(
        cls,
        message: str,
        status: str = "success",
    ) -> "ModelCliOutputData":
        """Create a simple output with just message and status."""
        return cls(message=message, status=status)

    @classmethod
    def create_node_list(cls, nodes: list[ModelNodeInfo]) -> "ModelCliOutputData":
        """Create output for node listing."""
        return cls(nodes=nodes, count=len(nodes), message=f"Found {len(nodes)} nodes")

    @classmethod
    def create_validation_result(
        cls,
        passed: bool,
        message: str,
        test_results: dict[str, bool] | None = None,
    ) -> "ModelCliOutputData":
        """Create output for validation results."""
        return cls(
            validation_passed=passed,
            message=message,
            status="success" if passed else "failed",
            test_results=test_results,
        )
