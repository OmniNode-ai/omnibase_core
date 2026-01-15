"""
Workflow Outputs Model

Type-safe workflow outputs that replace Dict[str, Any] usage
for workflow execution results.
"""

from typing import cast

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.services.model_custom_fields import ModelCustomFields
from omnibase_core.types.type_json import JsonType
from omnibase_core.types.type_serializable_value import SerializedDict
from omnibase_core.types.typed_dict_workflow_outputs import TypedDictWorkflowOutputsDict


class ModelWorkflowOutputs(BaseModel):
    """
    Type-safe workflow outputs.

    This model provides structured output storage for workflow execution
    results with type safety and validation.
    """

    model_config = ConfigDict(from_attributes=True)

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
    data: dict[str, ModelSchemaValue] | None = Field(
        default=None,
        description="Structured data outputs (type-safe)",
    )

    # For extensibility - custom fields that don't fit above
    custom_outputs: ModelCustomFields | None = Field(
        default=None,
        description="Custom output fields for workflow-specific data",
    )

    @field_serializer("data", when_used="always")
    def serialize_data(
        self, values: dict[str, ModelSchemaValue] | None
    ) -> dict[str, JsonType] | None:
        """
        Serialize data field by converting ModelSchemaValue to primitives.

        This ensures consistent serialization when using model_dump() or
        model_dump_json(), matching the behavior of to_dict().
        """
        if values is None:
            return None
        return {k: v.to_value() for k, v in values.items()}

    @field_serializer("custom_outputs", when_used="always")
    def serialize_custom_outputs(
        self, value: ModelCustomFields | None
    ) -> dict[str, object] | None:
        """
        Serialize custom_outputs field by converting ModelSchemaValue objects
        in field_values to primitives.

        This ensures consistent serialization when using model_dump() or
        model_dump_json(), matching the behavior of to_dict().

        Note: We exclude field_values from the initial model_dump() to prevent
        Pydantic from serializing ModelSchemaValue objects as nested dicts.
        We then manually add field_values with proper primitive conversion.
        """
        if value is None:
            return None

        # Serialize base model, excluding field_values to avoid double-serialization
        # of ModelSchemaValue objects (Pydantic would serialize them as nested dicts
        # with value_type, string_value, etc. instead of primitive values)
        result = value.model_dump(exclude_none=True, exclude={"field_values"})

        # Manually serialize field_values, converting ModelSchemaValue to primitives
        # Always include field_values (even if empty) for consistency
        result["field_values"] = {
            k: (v.to_value() if isinstance(v, ModelSchemaValue) else v)
            for k, v in value.field_values.items()
        }

        return result

    def add_output(
        self,
        key: str,
        value: ModelSchemaValue
        | str
        | int
        | float
        | bool
        | list[object]
        | dict[str, object]
        | None,
    ) -> None:
        """
        Add a custom output field.

        Args:
            key: Output field key
            value: Output field value (converted to ModelSchemaValue)
        """
        if self.custom_outputs is None:
            from omnibase_core.models.primitives.model_semver import ModelSemVer

            self.custom_outputs = ModelCustomFields(
                schema_version=ModelSemVer(major=1, minor=0, patch=0)
            )
        # Convert to ModelSchemaValue for type safety
        if not isinstance(value, ModelSchemaValue):
            value = ModelSchemaValue.from_value(value)
        # Use immutable API - with_field returns new instance
        self.custom_outputs = self.custom_outputs.with_field(key, value)

    def get_output(
        self, key: str, default: ModelSchemaValue | None = None
    ) -> ModelSchemaValue | None:
        """
        Get a custom output field.

        Args:
            key: Output field key
            default: Default value if not found

        Returns:
            ModelSchemaValue or default
        """
        if self.custom_outputs is None:
            return default
        value = self.custom_outputs.field_values.get(key)
        if value is None:
            return default
        # Ensure we return ModelSchemaValue
        if isinstance(value, ModelSchemaValue):
            return value
        return ModelSchemaValue.from_value(value)

    def to_dict(self) -> TypedDictWorkflowOutputsDict:
        """Convert to dictionary for current standards."""
        # Create dictionary with all standard fields and merge custom fields
        result: SerializedDict = {
            "result": self.result,
            "status_message": self.status_message,
            "error_message": self.error_message,
            # Convert list[str] to list for JsonType compatibility
            "generated_files": list(self.generated_files)
            if self.generated_files
            else None,
            "modified_files": list(self.modified_files)
            if self.modified_files
            else None,
            "execution_time_ms": self.execution_time_ms,
            "items_processed": self.items_processed,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }

        # Filter out None values from the result dict.
        # The comprehension produces dict[str, JsonType] which is SerializedDict.
        result = {k: v for k, v in result.items() if v is not None}

        # Add data if present (convert ModelSchemaValue to raw values)
        if self.data:
            # to_value() returns JsonType which is compatible with SerializedDict values
            result["data"] = {key: value.to_value() for key, value in self.data.items()}

        # Add custom outputs if present (convert ModelSchemaValue to primitives)
        if self.custom_outputs:
            # Exclude field_values from initial dump to avoid double-serialization
            custom_dump = self.custom_outputs.model_dump(
                exclude_none=True, exclude={"field_values"}
            )
            # Manually serialize field_values, converting ModelSchemaValue to primitives
            custom_dump["field_values"] = {
                k: (v.to_value() if isinstance(v, ModelSchemaValue) else v)
                for k, v in self.custom_outputs.field_values.items()
            }
            result.update(custom_dump)

        # Cast to TypedDict - the structure matches TypedDictWorkflowOutputsDict
        # Note: Using cast() because TypedDict is a structural type for static checking,
        # not a runtime constructor. The result dict is built to match the TypedDict schema.
        return cast(TypedDictWorkflowOutputsDict, result)
