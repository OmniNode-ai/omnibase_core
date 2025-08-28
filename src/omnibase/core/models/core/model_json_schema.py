"""
Model for representing JSON schema structures with proper type safety.

This model replaces dictionary usage when working with JSON schemas
by providing a structured representation of schema data.
"""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from omnibase.model.core.model_schema_value import ModelSchemaValue


class ModelJsonSchema(BaseModel):
    """
    Type-safe representation of JSON Schema structure.

    This model represents JSON Schema definitions without resorting to Any type usage.
    """

    # Core schema properties
    type: Optional[str] = Field(None, description="JSON Schema type")
    description: Optional[str] = Field(None, description="Schema description")
    title: Optional[str] = Field(None, description="Schema title")
    default: Optional[ModelSchemaValue] = Field(None, description="Default value")

    # String validation
    min_length: Optional[int] = Field(None, alias="minLength")
    max_length: Optional[int] = Field(None, alias="maxLength")
    pattern: Optional[str] = Field(None, description="String pattern")
    format: Optional[str] = Field(None, description="String format")

    # Numeric validation
    minimum: Optional[Union[int, float]] = Field(None, description="Minimum value")
    maximum: Optional[Union[int, float]] = Field(None, description="Maximum value")
    exclusive_minimum: Optional[bool] = Field(None, alias="exclusiveMinimum")
    exclusive_maximum: Optional[bool] = Field(None, alias="exclusiveMaximum")
    multiple_of: Optional[Union[int, float]] = Field(None, alias="multipleOf")

    # Array validation
    items: Optional["ModelJsonSchema"] = Field(None, description="Array items schema")
    min_items: Optional[int] = Field(None, alias="minItems")
    max_items: Optional[int] = Field(None, alias="maxItems")
    unique_items: Optional[bool] = Field(None, alias="uniqueItems")

    # Object validation
    properties: Optional[Dict[str, "ModelJsonSchema"]] = Field(
        None, description="Object properties"
    )
    required: Optional[List[str]] = Field(None, description="Required properties")
    additional_properties: Optional[Union[bool, "ModelJsonSchema"]] = Field(
        None, alias="additionalProperties"
    )

    # Composition
    all_of: Optional[List["ModelJsonSchema"]] = Field(None, alias="allOf")
    any_of: Optional[List["ModelJsonSchema"]] = Field(None, alias="anyOf")
    one_of: Optional[List["ModelJsonSchema"]] = Field(None, alias="oneOf")
    not_schema: Optional["ModelJsonSchema"] = Field(None, alias="not")

    # References
    ref: Optional[str] = Field(None, alias="$ref", description="Schema reference")
    definitions: Optional[Dict[str, "ModelJsonSchema"]] = Field(
        None, description="Schema definitions"
    )

    # Enumeration
    enum: Optional[List[ModelSchemaValue]] = Field(
        None, description="Enumeration values"
    )
    const: Optional[ModelSchemaValue] = Field(None, description="Constant value")

    # Additional metadata
    examples: Optional[List[ModelSchemaValue]] = Field(
        None, description="Example values"
    )
    deprecated: Optional[bool] = Field(None, description="Whether schema is deprecated")
    read_only: Optional[bool] = Field(None, alias="readOnly")
    write_only: Optional[bool] = Field(None, alias="writeOnly")

    class Config:
        populate_by_name = True  # Allow both field names and aliases

    @classmethod
    def from_dict(cls, schema_dict: dict) -> "ModelJsonSchema":
        """
        Create ModelJsonSchema from a dictionary.

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

        if "properties" in schema_dict and isinstance(schema_dict["properties"], dict):
            schema_dict["properties"] = {
                k: cls.from_dict(v) if isinstance(v, dict) else v
                for k, v in schema_dict["properties"].items()
            }

        if "additionalProperties" in schema_dict and isinstance(
            schema_dict["additionalProperties"], dict
        ):
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

        if "definitions" in schema_dict and isinstance(
            schema_dict["definitions"], dict
        ):
            schema_dict["definitions"] = {
                k: cls.from_dict(v) if isinstance(v, dict) else v
                for k, v in schema_dict["definitions"].items()
            }

        return cls(**schema_dict)

    def to_dict(self) -> dict:
        """
        Convert back to dictionary representation.

        Returns:
            Dictionary representation of the schema
        """
        result = {}

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
