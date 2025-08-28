"""
CLI Output Data Model

Structured model for CLI command execution output data,
replacing Dict[str, Any] with typed fields.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from omnibase.model.core.model_custom_fields import ModelCustomFields
from omnibase.model.core.model_node_info import ModelNodeInfo
from omnibase.model.core.model_node_metadata_info import ModelNodeMetadataInfo


class ModelCliOutputData(BaseModel):
    """
    Structured output data from CLI command execution.

    This model provides typed fields for common CLI output patterns
    while still allowing extensibility through custom fields.
    """

    # Common output fields
    message: Optional[str] = Field(None, description="Human-readable output message")

    status: Optional[str] = Field(None, description="Status indicator")

    # Node-related output
    nodes: Optional[List[ModelNodeInfo]] = Field(
        None, description="List of nodes (for discovery/list commands)"
    )

    node_info: Optional[ModelNodeInfo] = Field(
        None, description="Single node information"
    )

    node_metadata: Optional[ModelNodeMetadataInfo] = Field(
        None, description="Node metadata information"
    )

    # Registry-related output
    registry_count: Optional[int] = Field(
        None, description="Number of items in registry"
    )

    registry_status: Optional[str] = Field(
        None, description="Registry status information"
    )

    # Validation/test results
    validation_passed: Optional[bool] = Field(
        None, description="Whether validation passed"
    )

    test_results: Optional[Dict[str, bool]] = Field(
        None, description="Test results by test name"
    )

    # Scenario results
    scenario_name: Optional[str] = Field(None, description="Name of executed scenario")

    scenario_status: Optional[str] = Field(
        None, description="Scenario execution status"
    )

    # Config/settings output
    config_values: Optional[Dict[str, str]] = Field(
        None, description="Configuration values"
    )

    # File operation results
    files_processed: Optional[List[str]] = Field(
        None, description="List of processed files"
    )

    files_created: Optional[List[str]] = Field(
        None, description="List of created files"
    )

    files_modified: Optional[List[str]] = Field(
        None, description="List of modified files"
    )

    # Numeric results
    count: Optional[int] = Field(None, description="Generic count value")

    total: Optional[int] = Field(None, description="Total items")

    processed: Optional[int] = Field(None, description="Items processed")

    failed: Optional[int] = Field(None, description="Items failed")

    skipped: Optional[int] = Field(None, description="Items skipped")

    # Extended fields for complex outputs
    custom_fields: Optional[ModelCustomFields] = Field(
        None, description="Extensible custom fields for specific commands"
    )

    # Backward compatibility field for truly dynamic data
    # This should only be used when the structure is genuinely unknown
    raw_data: Optional[Dict[str, Any]] = Field(
        None, description="Raw unstructured data (use sparingly)"
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

    def to_dict(self, include_none: bool = False) -> Dict[str, Any]:
        """Convert to dictionary, optionally including None values."""
        data = {}

        # Add all non-None fields
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
    def from_dict(cls, data: Dict[str, Any]) -> "ModelCliOutputData":
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
        cls, message: str, status: str = "success"
    ) -> "ModelCliOutputData":
        """Create a simple output with just message and status."""
        return cls(message=message, status=status)

    @classmethod
    def create_node_list(cls, nodes: List[ModelNodeInfo]) -> "ModelCliOutputData":
        """Create output for node listing."""
        return cls(nodes=nodes, count=len(nodes), message=f"Found {len(nodes)} nodes")

    @classmethod
    def create_validation_result(
        cls, passed: bool, message: str, test_results: Optional[Dict[str, bool]] = None
    ) -> "ModelCliOutputData":
        """Create output for validation results."""
        return cls(
            validation_passed=passed,
            message=message,
            status="success" if passed else "failed",
            test_results=test_results,
        )
