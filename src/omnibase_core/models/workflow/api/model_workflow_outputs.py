"""
Workflow Outputs Model

Type-safe workflow outputs that replace Dict[str, Any] usage
for workflow execution results.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.services.model_custom_fields import ModelCustomFields
from omnibase_core.types.typed_dict_workflow_outputs import TypedDictWorkflowOutputsDict
from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "Workflow outputs output_data field requires dict[str, Any] for "
    "flexible workflow-specific result data and custom output formats."
)
class ModelWorkflowOutputs(BaseModel):
    """
    Type-safe workflow outputs.

    This model provides structured output storage for workflow execution
    results with type safety and validation.
    """

    # Common output fields
    result: str | None = Field(default=None, description="Main result value")
    status_message: str | None = Field(
        default=None,
        description="Human-readable status message",
    )
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )

    # Structured outputs
    generated_files: list[str] = Field(
        default_factory=list,
        description="List of generated file paths",
    )
    modified_files: list[str] = Field(
        default_factory=list,
        description="List of modified file paths",
    )

    # Metrics and statistics
    execution_time_ms: int | None = Field(
        default=None,
        description="Execution time in milliseconds",
    )
    items_processed: int | None = Field(
        default=None,
        description="Number of items processed",
    )
    success_count: int | None = Field(
        default=None,
        description="Number of successful operations",
    )
    failure_count: int | None = Field(
        default=None,
        description="Number of failed operations",
    )

    # Structured data outputs
    data: dict[str, str | int | float | bool | list[str]] | None = Field(
        default=None,
        description="Structured data outputs",
    )

    # For extensibility - custom fields that don't fit above
    custom_outputs: ModelCustomFields | None = Field(
        default=None,
        description="Custom output fields for workflow-specific data",
    )

    def add_output(self, key: str, value: Any) -> None:
        """
        Add a custom output field.

        Args:
            key: Output field key
            value: Output field value
        """
        if self.custom_outputs is None:
            from omnibase_core.models.primitives.model_semver import ModelSemVer

            self.custom_outputs = ModelCustomFields(
                schema_version=ModelSemVer(major=1, minor=0, patch=0)
            )
        self.custom_outputs.set_field(key, value)

    def get_output(self, key: str, default: Any = None) -> Any:
        """
        Get a custom output field.

        Args:
            key: Output field key
            default: Default value if not found

        Returns:
            Output value or default
        """
        if self.custom_outputs is None:
            return default
        return self.custom_outputs.field_values.get(key, default)

    def to_dict(self) -> TypedDictWorkflowOutputsDict:
        """Convert to dictionary for current standards."""
        # Create dictionary with all standard fields and merge custom fields
        result: dict[str, Any] = {
            "result": self.result,
            "status_message": self.status_message,
            "error_message": self.error_message,
            "generated_files": self.generated_files,
            "modified_files": self.modified_files,
            "execution_time_ms": self.execution_time_ms,
            "items_processed": self.items_processed,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }

        # Remove None values
        result = {k: v for k, v in result.items() if v is not None}

        # Add data if present
        if self.data:
            result["data"] = self.data

        # Add custom outputs if present
        if self.custom_outputs:
            result.update(self.custom_outputs.to_dict())

        # Cast to TypedDict - the structure matches TypedDictWorkflowOutputsDict
        return TypedDictWorkflowOutputsDict(**result)  # type: ignore[typeddict-item]
