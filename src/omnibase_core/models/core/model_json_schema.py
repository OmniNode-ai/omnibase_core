import json
from typing import Dict, Optional, Union

from pydantic import Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

"""
Model for representing JSON schema structures with proper type safety.

This model replaces dict[str, Any]ionary usage when working with JSON schemas
by providing a structured representation of schema data.
"""

from typing import Any

from pydantic import BaseModel

from omnibase_core.models.core.model_json_schema_config import ModelJsonSchemaConfig


class ModelJsonSchema(BaseModel):
    """
    Type-safe representation of JSON Schema structure.

    This model represents JSON Schema definitions without resorting to Any type usage.
    """

    # Core schema properties
    type: str | None = Field(default=None, description="JSON Schema type")
    description: str | None = Field(default=None, description="Schema description")
    title: str | None = Field(default=None, description="Schema title")
    default: ModelSchemaValue | None = Field(default=None, description="Default value")

    # String validation
    min_length: int | None = Field(default=None, alias="minLength")
    max_length: int | None = Field(default=None, alias="maxLength")
    pattern: str | None = Field(default=None, description="String pattern")
    format: str | None = Field(default=None, description="String format")

    # Numeric validation
    minimum: int | float | None = Field(default=None, description="Minimum value")
    maximum: int | float | None = Field(default=None, description="Maximum value")
    exclusive_minimum: bool | None = Field(default=None, alias="exclusiveMinimum")
    exclusive_maximum: bool | None = Field(default=None, alias="exclusiveMaximum")
    multiple_of: int | float | None = Field(default=None, alias="multipleOf")

    # Array validation
    items: Optional["ModelJsonSchema"] = Field(
        default=None, description="Array items schema"
    )
    min_items: int | None = Field(default=None, alias="minItems")
    max_items: int | None = Field(default=None, alias="maxItems")
    unique_items: bool | None = Field(default=None, alias="uniqueItems")

    # Object validation
    properties: dict[str, "ModelJsonSchema"] | None = Field(
        default=None, description="Object properties"
    )
    required: list[str] | None = Field(default=None, description="Required properties")
    additional_properties: Union[bool, "ModelJsonSchema"] | None = Field(
        default=None, alias="additionalProperties"
    )

    # Composition
    all_of: list["ModelJsonSchema"] | None = Field(default=None, alias="allOf")
    any_of: list["ModelJsonSchema"] | None = Field(default=None, alias="anyOf")
    one_of: list["ModelJsonSchema"] | None = Field(default=None, alias="oneOf")
    not_schema: Optional["ModelJsonSchema"] = Field(default=None, alias="not")

    # References
    ref: str | None = Field(default=None, alias="$ref", description="Schema reference")
    definitions: dict[str, "ModelJsonSchema"] | None = Field(
        default=None, description="Schema definitions"
    )

    # Enumeration
    enum: list[ModelSchemaValue] | None = Field(
        default=None, description="Enumeration values"
    )
    const: ModelSchemaValue | None = Field(default=None, description="Constant value")

    # Additional metadata
    examples: list[ModelSchemaValue] | None = Field(
        default=None, description="Example values"
    )
    deprecated: bool | None = Field(
        default=None, description="Whether schema is deprecated"
    )
    read_only: bool | None = Field(default=None, alias="readOnly")
    write_only: bool | None = Field(default=None, alias="writeOnly")

    @classmethod
    def from_dict(cls, schema_dict: dict[str, Any]) -> "ModelJsonSchema":
        """
        Create ModelJsonSchema from a dict[str, Any]ionary.

        Args:
            schema_dict: Dictionary representation of JSON schema

        Returns:
            ModelJsonSchema instance
        """
        # Convert enum values to ModelSchemaValue
        if "enum" in schema_dict:
            schema_dict["enum"] = [
                ModelSchemaValue.from_value(v) for v in schema_dict["enum"]
            ]

        # Convert default value
        if "default" in schema_dict:
            schema_dict["default"] = ModelSchemaValue.from_value(schema_dict["default"])

        # Convert const value
        if "const" in schema_dict:
            schema_dict["const"] = ModelSchemaValue.from_value(schema_dict["const"])

        # Convert examples
        if "examples" in schema_dict:
            schema_dict["examples"] = [
                ModelSchemaValue.from_value(v) for v in schema_dict["examples"]
            ]

        # Recursively convert nested schemas
        if "items" in schema_dict and isinstance(schema_dict["items"], dict):
            schema_dict["items"] = cls.from_dict(schema_dict["items"])

        if "properties" in schema_dict and isinstance(schema_dict, dict):
            schema_dict["properties"] = {
                k: cls.from_dict(v) if isinstance(v, dict) else v
                for k, v in schema_dict["properties"].items()
            }

        if "additionalProperties" in schema_dict and isinstance(schema_dict, dict):
            schema_dict["additionalProperties"] = cls.from_dict(
                schema_dict["additionalProperties"]
            )

        # Handle composition schemas
        for field in ["allOf", "anyOf", "oneOf"]:
            if field in schema_dict and isinstance(schema_dict[field], list):
                schema_dict[field] = [
                    cls.from_dict(s) if isinstance(s, dict) else s
                    for s in schema_dict[field]
                ]

        if "not" in schema_dict and isinstance(schema_dict["not"], dict):
            schema_dict["not_schema"] = cls.from_dict(schema_dict["not"])
            del schema_dict["not"]

        if "definitions" in schema_dict and isinstance(schema_dict, dict):
            schema_dict["definitions"] = {
                k: cls.from_dict(v) if isinstance(v, dict) else v
                for k, v in schema_dict["definitions"].items()
            }

        return cls(**schema_dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert back to dict[str, Any]ionary representation.

        Returns:
            Dictionary representation of the schema
        """
        # Custom reconstruction logic for JSON schema format
        result: dict[str, Any] = {}

        # Add basic properties
        if self.type:
            result["type"] = self.type
        if self.description:
            result["description"] = self.description
        if self.title:
            result["title"] = self.title
        if self.default:
            result["default"] = self.default.to_value()

        # Add string validation
        if self.min_length is not None:
            result["minLength"] = self.min_length
        if self.max_length is not None:
            result["maxLength"] = self.max_length
        if self.pattern:
            result["pattern"] = self.pattern
        if self.format:
            result["format"] = self.format

        # Add numeric validation
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        if self.exclusive_minimum is not None:
            result["exclusiveMinimum"] = self.exclusive_minimum
        if self.exclusive_maximum is not None:
            result["exclusiveMaximum"] = self.exclusive_maximum
        if self.multiple_of is not None:
            result["multipleOf"] = self.multiple_of

        # Add array validation
        if self.items:
            result["items"] = self.items.to_dict()
        if self.min_items is not None:
            result["minItems"] = self.min_items
        if self.max_items is not None:
            result["maxItems"] = self.max_items
        if self.unique_items is not None:
            result["uniqueItems"] = self.unique_items

        # Add object validation
        if self.properties:
            result["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        if self.required:
            result["required"] = self.required
        if self.additional_properties is not None:
            if isinstance(self.additional_properties, bool):
                result["additionalProperties"] = self.additional_properties
            else:
                result["additionalProperties"] = self.additional_properties.to_dict()

        # Add composition
        if self.all_of:
            result["allOf"] = [s.to_dict() for s in self.all_of]
        if self.any_of:
            result["anyOf"] = [s.to_dict() for s in self.any_of]
        if self.one_of:
            result["oneOf"] = [s.to_dict() for s in self.one_of]
        if self.not_schema:
            result["not"] = self.not_schema.to_dict()

        # Add references
        if self.ref:
            result["$ref"] = self.ref
        if self.definitions:
            result["definitions"] = {
                k: v.to_dict() for k, v in self.definitions.items()
            }

        # Add enumeration
        if self.enum:
            result["enum"] = [v.to_value() for v in self.enum]
        if self.const:
            result["const"] = self.const.to_value()

        # Add metadata
        if self.examples:
            result["examples"] = [v.to_value() for v in self.examples]
        if self.deprecated is not None:
            result["deprecated"] = self.deprecated
        if self.read_only is not None:
            result["readOnly"] = self.read_only
        if self.write_only is not None:
            result["writeOnly"] = self.write_only

        return result
