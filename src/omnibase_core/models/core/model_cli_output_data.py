"""
CLI Output Data Model.

Structured model for CLI command execution output data,
replacing Dict[str, Any] with strongly typed fields.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_cli_status import EnumCliStatus
from omnibase_core.enums.enum_registry_status import EnumRegistryStatus
from omnibase_core.enums.enum_scenario_status import EnumScenarioStatus
from omnibase_core.models.core.model_custom_fields import ModelCustomFields
from omnibase_core.models.core.model_node_info import ModelNodeInfo
from omnibase_core.models.core.model_node_metadata_info import ModelNodeMetadataInfo

from .model_generic_metadata import ModelGenericMetadata
from .model_test_results import ModelTestResults


class ModelCliOutputData(BaseModel):
    """
    Structured output data from CLI command execution.

    This model provides strongly typed fields for common CLI output patterns
    with no magic strings or poorly typed dictionaries.
    """

    # Core output fields (always present)
    message: str = Field(default="", description="Human-readable output message")
    status: EnumCliStatus = Field(
        default=EnumCliStatus.SUCCESS, description="Strongly typed status"
    )

    # Node-related output
    nodes: List[ModelNodeInfo] = Field(
        default_factory=list,
        description="List of nodes (for discovery/list commands)",
    )

    node_info: ModelNodeInfo | None = Field(
        default=None,
        description="Single node information (only when applicable)",
    )

    node_metadata: ModelNodeMetadataInfo | None = Field(
        default=None,
        description="Node metadata information (only when applicable)",
    )

    # Registry-related output
    registry_count: int = Field(
        default=0,
        description="Number of items in registry",
        ge=0,
    )

    registry_status: EnumRegistryStatus = Field(
        default=EnumRegistryStatus.HEALTHY,
        description="Strongly typed registry status",
    )

    # Validation/test results (strongly typed)
    validation_passed: bool = Field(
        default=True,
        description="Whether validation passed",
    )

    test_results: ModelTestResults = Field(
        default_factory=ModelTestResults,
        description="Strongly typed test results",
    )

    # Scenario results
    scenario_name: str = Field(default="", description="Name of executed scenario")

    scenario_status: EnumScenarioStatus = Field(
        default=EnumScenarioStatus.NOT_EXECUTED,
        description="Strongly typed scenario status",
    )

    # Config/settings output (only when applicable)
    config_details: ModelGenericMetadata | None = Field(
        default=None,
        description="Configuration values (only for config operations)",
    )

    # File operation results
    files_processed: List[str] = Field(
        default_factory=list,
        description="List of processed files",
    )

    files_created: List[str] = Field(
        default_factory=list,
        description="List of created files",
    )

    files_modified: List[str] = Field(
        default_factory=list,
        description="List of modified files",
    )

    # Numeric results (always have defaults)
    count: int = Field(default=0, description="Generic count value", ge=0)
    total: int = Field(default=0, description="Total items", ge=0)
    processed: int = Field(default=0, description="Items processed", ge=0)
    failed: int = Field(default=0, description="Items failed", ge=0)
    skipped: int = Field(default=0, description="Items skipped", ge=0)

    # Extended fields (only when truly needed)
    custom_fields: ModelCustomFields | None = Field(
        default=None,
        description="Extensible custom fields (only when standard fields insufficient)",
    )

    def get_field_value(self, field_name: str, default: Any = None) -> Any:
        """Get a field value by name with strong typing."""
        # Only check direct fields - no fallbacks to dictionaries
        if hasattr(self, field_name):
            value = getattr(self, field_name)
            if value is not None:
                return str(value) if value else ""

        # Check custom fields only if they exist
        if self.custom_fields:
            return self.custom_fields.get_string(
                field_name, str(default) if default else ""
            )

        return default

    def set_field_value(self, field_name: str, value: Any) -> None:
        """Set a field value with strong typing enforcement."""
        # If it's a known field, set it directly with type validation
        if hasattr(self, field_name) and field_name != "custom_fields":
            # Validate the type matches the field definition
            field_info = self.model_fields.get(field_name)
            if field_info:
                setattr(self, field_name, value)
            else:
                raise ValueError(
                    f"Cannot set field {field_name}: field type validation failed"
                )
        else:
            # Use custom fields for extension
            if not self.custom_fields:
                self.custom_fields = ModelCustomFields()
            # Enforce allowed custom field types only
            if isinstance(value, (str, int, bool, float, list)):
                self.custom_fields.set_field(field_name, value)
            else:
                raise ValueError(
                    f"Custom field {field_name} must be str, int, bool, float, or list"
                )

    def to_dict(self, include_none: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with strong typing preserved."""
        data: Dict[str, Any] = {}

        # Add all standard fields
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
        """Create from dictionary with strict type validation."""
        known_fields = set(cls.model_fields.keys())
        standard_data: Dict[str, Any] = {}
        custom_data: Dict[str, Any] = {}

        for key, value in data.items():
            if key in known_fields:
                standard_data[key] = value
            else:
                custom_data[key] = value

        # Create instance with standard fields (Pydantic will validate types)
        instance = cls(**standard_data)

        # Add custom fields with type validation
        if custom_data:
            instance.custom_fields = ModelCustomFields()
            for key, value in custom_data.items():
                if isinstance(value, (str, int, bool, float, list)):
                    instance.custom_fields.set_field(key, value)
                else:
                    raise ValueError(
                        f"Custom field {key} has invalid type: {type(value)}"
                    )

        return instance

    @classmethod
    def create_simple(
        cls,
        message: str,
        status: EnumCliStatus = EnumCliStatus.SUCCESS,
    ) -> "ModelCliOutputData":
        """Create a simple output with message and status."""
        return cls(message=message, status=status)

    @classmethod
    def create_node_list(cls, nodes: List[ModelNodeInfo]) -> "ModelCliOutputData":
        """Create output for node listing."""
        return cls(
            nodes=nodes,
            count=len(nodes),
            total=len(nodes),
            message=f"Found {len(nodes)} nodes",
            status=EnumCliStatus.SUCCESS,
        )

    @classmethod
    def create_validation_result(
        cls,
        passed: bool,
        message: str,
        test_results: ModelTestResults,
    ) -> "ModelCliOutputData":
        """Create output for validation results."""
        return cls(
            validation_passed=passed,
            message=message,
            status=EnumCliStatus.SUCCESS if passed else EnumCliStatus.FAILED,
            test_results=test_results,
        )


# Export for use
__all__ = ["ModelCliOutputData"]
