"""
Model for representing schema dictionaries with proper type safety.

This model replaces dictionary usage in schema definitions by providing
a structured representation of schema dictionaries.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelSchemaDict(BaseModel):
    """
    Type-safe representation of schema dictionaries.

    This model represents JSON Schema objects as structured data without
    using untyped dictionaries.
    """

    # Core schema fields
    type: str | None = Field(default=None, description="JSON Schema type")
    schema_uri: str | None = Field(
        default=None,
        alias="$schema",
        description="Schema version URI",
    )
    title: str | None = Field(default=None, description="Schema title")
    description: str | None = Field(default=None, description="Schema description")
    ref: str | None = Field(
        default=None,
        alias="$ref",
        description="Reference to another schema",
    )

    # String constraints
    enum: list[str] | None = Field(default=None, description="Enumeration values")
    pattern: str | None = Field(default=None, description="String pattern")
    min_length: int | None = Field(
        default=None,
        alias="minLength",
        description="Minimum string length",
    )
    max_length: int | None = Field(
        default=None,
        alias="maxLength",
        description="Maximum string length",
    )

    # Numeric constraints
    minimum: int | float | None = Field(default=None, description="Minimum value")
    maximum: int | float | None = Field(default=None, description="Maximum value")
    multiple_of: int | float | None = Field(
        default=None,
        alias="multipleOf",
        description="Multiple of constraint",
    )

    # Array constraints
    items: ModelSchemaDict | None = Field(
        default=None, description="Array items schema"
    )
    min_items: int | None = Field(
        default=None,
        alias="minItems",
        description="Minimum array items",
    )
    max_items: int | None = Field(
        default=None,
        alias="maxItems",
        description="Maximum array items",
    )
    unique_items: bool | None = Field(
        default=None,
        alias="uniqueItems",
        description="Unique items constraint",
    )

    # Object constraints
    properties: dict[str, ModelSchemaDict] | None = Field(
        default=None,
        description="Object properties",
    )
    required: list[str] | None = Field(default=None, description="Required properties")
    additional_properties: bool | ModelSchemaDict | None = Field(
        default=None,
        alias="additionalProperties",
        description="Additional properties constraint",
    )
    min_properties: int | None = Field(
        default=None,
        alias="minProperties",
        description="Minimum properties",
    )
    max_properties: int | None = Field(
        default=None,
        alias="maxProperties",
        description="Maximum properties",
    )

    # General constraints
    nullable: bool | None = Field(default=None, description="Nullable constraint")
    default: ModelSchemaValue | None = Field(default=None, description="Default value")

    # Schema composition
    definitions: dict[str, ModelSchemaDict] | None = Field(
        default=None,
        description="Schema definitions",
    )
    all_of: list[ModelSchemaDict] | None = Field(
        default=None,
        alias="allOf",
        description="All of composition",
    )
    any_of: list[ModelSchemaDict] | None = Field(
        default=None,
        alias="anyOf",
        description="Any of composition",
    )
    one_of: list[ModelSchemaDict] | None = Field(
        default=None,
        alias="oneOf",
        description="One of composition",
    )

    # Examples
    examples: list[ModelSchemaValue] | None = Field(
        default=None,
        description="Example values",
    )

    # Additional properties for completeness
    additional_fields: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Additional schema fields",
    )

    def to_dict(self) -> dict[str, object]:
        """
        Convert to standard dictionary format.

        Returns:
            Dictionary representation
        """
        # Custom reconstruction logic for schema dictionary format
        result: dict[str, object] = {}

        # Add core fields
        if self.type is not None:
            result["type"] = self.type
        if self.schema_uri is not None:
            result["$schema"] = self.schema_uri
        if self.title is not None:
            result["title"] = self.title
        if self.description is not None:
            result["description"] = self.description
        if self.ref is not None:
            result["$ref"] = self.ref

        # Add string constraints
        if self.enum is not None:
            result["enum"] = self.enum
        if self.pattern is not None:
            result["pattern"] = self.pattern
        if self.min_length is not None:
            result["minLength"] = self.min_length
        if self.max_length is not None:
            result["maxLength"] = self.max_length

        # Add numeric constraints
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        if self.multiple_of is not None:
            result["multipleOf"] = self.multiple_of

        # Add array constraints
        if self.items is not None:
            result["items"] = self.items.to_dict()
        if self.min_items is not None:
            result["minItems"] = self.min_items
        if self.max_items is not None:
            result["maxItems"] = self.max_items
        if self.unique_items is not None:
            result["uniqueItems"] = self.unique_items

        # Add object constraints
        if self.properties is not None:
            result["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        if self.required is not None:
            result["required"] = self.required
        if self.additional_properties is not None:
            if isinstance(self.additional_properties, bool):
                result["additionalProperties"] = self.additional_properties
            else:
                result["additionalProperties"] = self.additional_properties.to_dict()
        if self.min_properties is not None:
            result["minProperties"] = self.min_properties
        if self.max_properties is not None:
            result["maxProperties"] = self.max_properties

        # Add general constraints
        if self.nullable is not None:
            result["nullable"] = self.nullable
        if self.default is not None:
            result["default"] = self.default.to_value()

        # Add schema composition
        if self.definitions is not None:
            result["definitions"] = {
                k: v.to_dict() for k, v in self.definitions.items()
            }
        if self.all_of is not None:
            result["allOf"] = [s.to_dict() for s in self.all_of]
        if self.any_of is not None:
            result["anyOf"] = [s.to_dict() for s in self.any_of]
        if self.one_of is not None:
            result["oneOf"] = [s.to_dict() for s in self.one_of]

        # Add examples
        if self.examples is not None:
            result["examples"] = [ex.to_value() for ex in self.examples]

        # Add additional fields
        for key, value in self.additional_fields.items():
            if key not in result:
                result[key] = value.to_value()

        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ModelSchemaDict:
        """
        Create from dictionary.

        Args:
            data: Dictionary to convert

        Returns:
            ModelSchemaDict instance
        """
        # Extract known fields
        known_fields = {
            "type",
            "$schema",
            "title",
            "description",
            "$ref",
            "enum",
            "pattern",
            "minLength",
            "maxLength",
            "minimum",
            "maximum",
            "multipleOf",
            "items",
            "minItems",
            "maxItems",
            "uniqueItems",
            "properties",
            "required",
            "additionalProperties",
            "minProperties",
            "maxProperties",
            "nullable",
            "default",
            "definitions",
            "allOf",
            "anyOf",
            "oneOf",
            "examples",
        }

        # Build kwargs
        kwargs: dict[str, object] = {}
        additional_fields: dict[str, ModelSchemaValue] = {}

        for key, value in data.items():
            if key == "items" and isinstance(value, dict):
                kwargs["items"] = cls.from_dict(value)
            elif key == "properties" and isinstance(value, dict):
                kwargs["properties"] = {k: cls.from_dict(v) for k, v in value.items()}
            elif key == "additionalProperties":
                if isinstance(value, bool):
                    kwargs["additional_properties"] = value
                elif isinstance(value, dict):
                    kwargs["additional_properties"] = cls.from_dict(value)
            elif key == "definitions" and isinstance(value, dict):
                kwargs["definitions"] = {k: cls.from_dict(v) for k, v in value.items()}
            elif key in ["allOf", "anyOf", "oneOf"] and isinstance(value, list):
                field_name = key[0].lower() + key[1:-1] + "_of"
                kwargs[field_name] = [cls.from_dict(v) for v in value]
            elif key == "default":
                kwargs["default"] = ModelSchemaValue.from_value(value)
            elif key == "examples" and isinstance(value, list):
                kwargs["examples"] = [ModelSchemaValue.from_value(ex) for ex in value]
            elif key in known_fields:
                # Map to appropriate field name
                if key == "$schema":
                    kwargs["schema_uri"] = value
                elif key == "$ref":
                    kwargs["ref"] = value
                elif key == "minLength":
                    kwargs["min_length"] = value
                elif key == "maxLength":
                    kwargs["max_length"] = value
                elif key == "multipleOf":
                    kwargs["multiple_of"] = value
                elif key == "minItems":
                    kwargs["min_items"] = value
                elif key == "maxItems":
                    kwargs["max_items"] = value
                elif key == "uniqueItems":
                    kwargs["unique_items"] = value
                elif key == "minProperties":
                    kwargs["min_properties"] = value
                elif key == "maxProperties":
                    kwargs["max_properties"] = value
                else:
                    kwargs[key] = value
            else:
                # Unknown field - add to additional_fields
                additional_fields[key] = ModelSchemaValue.from_value(value)

        kwargs["additional_fields"] = additional_fields
        # Pydantic validates the data at runtime - type safety is enforced by Pydantic
        return cls.model_validate(kwargs)
