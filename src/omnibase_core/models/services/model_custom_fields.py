"""
Custom fields model to replace dictionary usage for custom/extensible fields.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.

Thread Safety:
    ModelCustomFields is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access. All modification methods return
    new instances rather than mutating in place.

    Migration from mutable API:
        # Old (mutable - no longer supported):
        fields.set_field("key", value)
        fields.remove_field("key")
        fields.define_field("key", "string")

        # New (immutable - returns new instance):
        fields = fields.with_field("key", value)
        fields = fields.without_field("key")
        fields = fields.with_field_definition("key", "string")
"""

from datetime import UTC, datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_decorators import allow_any_type, allow_dict_str_any

# Import separated models
from .model_custom_field_definition import ModelCustomFieldDefinition


@allow_any_type(
    "Custom field values need Any type for flexibility in graph nodes, orchestrator steps, and metadata",
)
@allow_dict_str_any(
    "Custom fields require dict[str, Any] for user-defined dynamic field values and batch operations",
)
class ModelCustomFields(BaseModel):
    """
    Immutable custom fields with typed structure and validation.

    Replaces Dict[str, Any] for custom fields with proper type safety.

    Thread Safety:
        This model is frozen (immutable) after creation. All modification
        methods (with_field, without_field, with_field_definition) return
        new instances rather than mutating in place. This makes the model
        safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.primitives import ModelSemVer
        >>> fields = ModelCustomFields(schema_version=ModelSemVer(major=1, minor=0, patch=0))
        >>> fields = fields.with_field("count", 42)
        >>> fields = fields.with_field("name", "example")
        >>> print(fields.get_field("count"))  # 42
    """

    # Field definitions (schema)
    field_definitions: dict[str, ModelCustomFieldDefinition] = Field(
        default_factory=dict,
        description="Custom field definitions",
    )

    field_values: dict[str, Any] = (
        Field(  # dict-any-ok: dynamic user-defined field values
            default_factory=dict,
            description="Custom field values",
        )
    )

    # Metadata
    schema_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Schema version",
    )
    last_modified: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last modification time",
    )
    modified_by: str | None = Field(default=None, description="Last modifier")

    # Validation settings
    strict_validation: bool = Field(
        default=False, description="Enforce strict validation"
    )
    allow_undefined_fields: bool = Field(
        default=True,
        description="Allow fields not in definitions",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    @field_validator("field_values")
    @classmethod
    def validate_field_values(cls, v: Any, info: Any = None) -> Any:
        """Validate field values against definitions."""
        values = info.data if info and hasattr(info, "data") else {}
        definitions = values.get("field_definitions", {})
        strict = values.get("strict_validation", False)
        allow_undefined = values.get("allow_undefined_fields", True)

        if strict and definitions:
            # Check required fields
            for name, definition in definitions.items():
                if definition.required and name not in v:
                    msg = f"Required field '{name}' is missing"
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=msg,
                    )

            # Check undefined fields
            if not allow_undefined:
                for name in v:
                    if name not in definitions:
                        msg = f"Undefined field '{name}' not allowed"
                        raise ModelOnexError(
                            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                            message=msg,
                        )

        return v

    # REMOVED: to_dict deprecated method - use model_dump(exclude_none=True) instead
    # REMOVED: from_dict factory method - use Pydantic model_validate() instead
    # Factory methods bypass Pydantic validation and violate ONEX architecture.
    # Migration: Replace ModelCustomFields.from_dict(data) with ModelCustomFields(**data)

    def get_field(self, name: str, default: Any = None) -> Any:
        """Get a custom field value.

        Args:
            name: Field name to retrieve.
            default: Default value if field doesn't exist.

        Returns:
            The field value, or default if not found.
        """
        return self.field_values.get(name, default)

    def with_field(
        self, name: str, value: Any, *, modified_by: str | None = None
    ) -> Self:
        """Return a new instance with the field set.

        This is an immutable operation - the original instance is not modified.

        Args:
            name: Field name to set.
            value: Value to assign to the field.
            modified_by: Optional identifier of who made the change.

        Returns:
            New ModelCustomFields instance with the field set.

        Raises:
            ModelOnexError: If strict_validation is enabled and value type
                doesn't match the field definition.
        """
        if self.strict_validation and name in self.field_definitions:
            definition = self.field_definitions[name]
            # Basic type validation
            if definition.field_type == "string" and not isinstance(value, str):
                msg = f"Field '{name}' must be a string"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )
            if definition.field_type == "number" and not isinstance(
                value,
                int | float,
            ):
                msg = f"Field '{name}' must be a number"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )
            if definition.field_type == "boolean" and not isinstance(value, bool):
                msg = f"Field '{name}' must be a boolean"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

        new_values = {**self.field_values, name: value}
        return self.model_copy(
            update={
                "field_values": new_values,
                "last_modified": datetime.now(UTC),
                "modified_by": modified_by or self.modified_by,
            }
        )

    def without_field(self, name: str, *, modified_by: str | None = None) -> Self:
        """Return a new instance with the field removed.

        This is an immutable operation - the original instance is not modified.

        Args:
            name: Field name to remove.
            modified_by: Optional identifier of who made the change.

        Returns:
            New ModelCustomFields instance without the field.
            If the field doesn't exist, returns a copy with updated timestamp.
        """
        new_values = {k: v for k, v in self.field_values.items() if k != name}
        return self.model_copy(
            update={
                "field_values": new_values,
                "last_modified": datetime.now(UTC),
                "modified_by": modified_by or self.modified_by,
            }
        )

    def with_field_definition(
        self,
        name: str,
        field_type: str,
        *,
        modified_by: str | None = None,
        **kwargs: Any,
    ) -> Self:
        """Return a new instance with a field definition added.

        This is an immutable operation - the original instance is not modified.

        Args:
            name: Field name to define.
            field_type: Type of the field (e.g., "string", "number", "boolean").
            modified_by: Optional identifier of who made the change.
            **kwargs: Additional arguments passed to ModelCustomFieldDefinition.

        Returns:
            New ModelCustomFields instance with the field definition added.
        """
        new_definition = ModelCustomFieldDefinition(
            field_name=name,
            field_type=field_type,
            **kwargs,
        )
        new_definitions = {**self.field_definitions, name: new_definition}
        return self.model_copy(
            update={
                "field_definitions": new_definitions,
                "last_modified": datetime.now(UTC),
                "modified_by": modified_by or self.modified_by,
            }
        )

    def with_fields(
        self, fields: dict[str, Any], *, modified_by: str | None = None
    ) -> Self:
        """Return a new instance with multiple fields set.

        This is an immutable operation - the original instance is not modified.

        Args:
            fields: Dictionary of field names to values.
            modified_by: Optional identifier of who made the change.

        Returns:
            New ModelCustomFields instance with all fields set.

        Raises:
            ModelOnexError: If strict_validation is enabled and any value type
                doesn't match its field definition.
        """
        result = self
        for name, value in fields.items():
            result = result.with_field(name, value, modified_by=modified_by)
        return result

    @field_serializer("last_modified")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None


# Re-export for current standards
# Note: ModelErrorDetails is NOT re-exported here to avoid circular imports.
# Import it directly from: omnibase_core.models.services.model_error_details
__all__ = [
    "ModelCustomFieldDefinition",
    "ModelCustomFields",
]
