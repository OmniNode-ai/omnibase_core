from typing import Dict, Optional

from pydantic import Field, field_validator

from omnibase_core.models.core.model_custom_fields import ModelCustomFields

"""
Custom fields model to replace dict[str, Any]ionary usage for custom/extensible fields.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from omnibase_core.utils.decorators import allow_any_type, allow_dict_str_any

# Import separated models
from .model_custom_field_definition import ModelCustomFieldDefinition
from .model_error_details import ModelErrorDetails


@allow_dict_str_any(
    "Custom fields require flexible dict[str, Any]ionary for extensibility across 20+ models",
)
@allow_any_type(
    "Custom field values need Any type for flexibility in graph nodes, orchestrator steps, and metadata",
)
class ModelCustomFields(BaseModel):
    """
    Custom fields with typed structure and validation.
    Replaces Dict[str, Any] for custom fields.
    """

    # Field definitions (schema)
    field_definitions: dict[str, ModelCustomFieldDefinition] = Field(
        default_factory=dict,
        description="Custom field definitions",
    )

    # Field values
    field_values: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom field values",
    )

    # Metadata
    schema_version: str = Field("1.0", description="Schema version")
    last_modified: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last modification time",
    )
    modified_by: str | None = Field(None, description="Last modifier")

    # Validation settings
    strict_validation: bool = Field(False, description="Enforce strict validation")
    allow_undefined_fields: bool = Field(
        True,
        description="Allow fields not in definitions",
    )

    model_config = ConfigDict()

    @field_validator("field_values")
    @classmethod
    def validate_field_values(cls, v, info=None):
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
                    raise ValueError(msg)

            # Check undefined fields
            if not allow_undefined:
                for name in v:
                    if name not in definitions:
                        msg = f"Undefined field '{name}' not allowed"
                        raise ValueError(msg)

        return v

    # DEPRECATED: Use model_dump(exclude_none=True) instead
    def to_dict(self) -> dict[str, Any]:
        """
        DEPRECATED: Use model_dump(exclude_none=True) instead.

        Convert to dict[str, Any]ionary for current standards.
        This method will be removed in a future release.
        """
        # Custom compatibility logic - return just the field values
        return self.field_values.copy()

    # REMOVED: from_dict factory method - use Pydantic model_validate() instead
    # Factory methods bypass Pydantic validation and violate ONEX architecture.
    # Migration: Replace ModelCustomFields.from_dict(data) with ModelCustomFields(**data)

    def get_field(self, name: str, default: Any = None) -> Any:
        """Get a custom field value."""
        return self.field_values.get(name, default)

    def set_field(self, name: str, value: Any):
        """Set a custom field value."""
        if self.strict_validation and name in self.field_definitions:
            definition = self.field_definitions[name]
            # Basic type validation
            if definition.field_type == "string" and not isinstance(value, str):
                msg = f"Field '{name}' must be a string"
                raise ValueError(msg)
            if definition.field_type == "number" and not isinstance(
                value,
                int | float,
            ):
                msg = f"Field '{name}' must be a number"
                raise ValueError(msg)
            if definition.field_type == "boolean" and not isinstance(value, bool):
                msg = f"Field '{name}' must be a boolean"
                raise ValueError(msg)

        self.field_values[name] = value
        self.last_modified = datetime.utcnow()

    def remove_field(self, name: str):
        """Remove a custom field."""
        if name in self.field_values:
            del self.field_values[name]
            self.last_modified = datetime.utcnow()

    def define_field(self, name: str, field_type: str, **kwargs):
        """Define a new custom field."""
        self.field_definitions[name] = ModelCustomFieldDefinition(
            field_name=name,
            field_type=field_type,
            **kwargs,
        )

    @field_serializer("last_modified")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value


# Compatibility aliases
CustomFieldDefinition = ModelCustomFieldDefinition
CustomFields = ModelCustomFields
ErrorDetails = ModelErrorDetails

# Re-export for current standards
__all__ = [
    # Compatibility
    "CustomFieldDefinition",
    "CustomFields",
    "ErrorDetails",
    "ModelCustomFieldDefinition",
    "ModelCustomFields",
    "ModelErrorDetails",
]
