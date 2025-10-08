import json
import uuid
from typing import Dict, Optional

from pydantic import Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_semver import ModelSemVer, parse_semver_from_string

"\nUnified Schema Model for JSON Schema representation.\n\nThis module contains a unified ModelSchema class that can represent both\nfull JSON Schema documents and individual schema properties, eliminating\nthe need for separate ModelSchemaDefinition and ModelPropertySchema classes.\n"
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_examples import ModelExample

from .model_typedproperties import ModelTypedProperties


class ModelSchema(BaseModel):
    """
    Unified schema model for JSON Schema representation.

    This class can represent both full JSON Schema documents and individual
    properties within schemas, providing a single unified interface for
    all schema operations.
    """

    model_config = ConfigDict(populate_by_name=True)
    schema_type: str = Field(
        default="object",
        alias="type",
        description="JSON Schema type (string, object, array, etc.)",
    )
    description: str | None = Field(
        default=None, description="Schema/property description"
    )
    ref: str | None = Field(
        default=None, alias="$ref", description="JSON Schema $ref reference"
    )
    schema_version: str = Field(default="draft-07", description="JSON Schema version")
    title: str | None = Field(default=None, description="Schema title")
    enum_values: list[str] | None = Field(
        default=None, alias="enum", description="Enum values for string types"
    )
    pattern: str | None = Field(default=None, description="Regex pattern for strings")
    format: str | None = Field(
        default=None,
        description="String format specifier (e.g., date-time, date, uuid)",
    )
    min_length: int | None = Field(
        default=None, alias="minLength", description="Minimum string length"
    )
    max_length: int | None = Field(
        default=None, alias="maxLength", description="Maximum string length"
    )
    minimum: int | float | None = Field(
        default=None, description="Minimum numeric value"
    )
    maximum: int | float | None = Field(
        default=None, description="Maximum numeric value"
    )
    multiple_of: int | float | None = Field(
        default=None, description="Numeric multiple constraint"
    )
    items: Optional["ModelSchema"] = Field(
        default=None, description="Array item schema"
    )
    min_items: int | None = Field(default=None, description="Minimum array length")
    max_items: int | None = Field(default=None, description="Maximum array length")
    unique_items: bool | None = Field(
        default=None, description="Whether array items must be unique"
    )
    properties: dict[str, "ModelSchema"] | None = Field(
        default=None, description="Object properties"
    )
    required: list[str] | None = Field(
        default=None, description="Required properties for objects"
    )
    additional_properties: bool | None = Field(
        default=True, description="Allow additional properties"
    )
    min_properties: int | None = Field(
        default=None, description="Minimum number of properties"
    )
    max_properties: int | None = Field(
        default=None, description="Maximum number of properties"
    )
    nullable: bool = Field(default=False, description="Whether property can be null")
    default_value: ModelSchemaValue | None = Field(
        default=None, description="Default value"
    )
    definitions: dict[str, "ModelSchema"] | None = Field(
        default=None, description="Reusable schema definitions"
    )
    all_of: list["ModelSchema"] | None = Field(
        default=None, description="All of constraints"
    )
    any_of: list["ModelSchema"] | None = Field(
        default=None, description="Any of constraints"
    )
    one_of: list["ModelSchema"] | None = Field(
        default=None, description="One of constraints"
    )
    examples: list[ModelExample] | None = Field(
        default=None, description="Example valid instances"
    )

    def is_resolved(self) -> bool:
        """Check if this schema has any unresolved $ref references."""
        if self.ref is not None:
            return False
        if self.items and (not self.items.is_resolved()):
            return False
        if self.properties:
            for prop in self.properties.values():
                if not prop.is_resolved():
                    return False
        if self.definitions:
            for definition in self.definitions.values():
                if not definition.is_resolved():
                    return False
        for schema_list in [self.all_of, self.any_of, self.one_of]:
            if schema_list:
                for schema in schema_list:
                    if not schema.is_resolved():
                        return False
        return True

    def resolve_refs(
        self, definitions: dict[str, "ModelSchema"] | None = None
    ) -> "ModelSchema":
        """
        Resolve $ref references in this schema.

        Args:
            definitions: Available schema definitions for resolution

        Returns:
            New ModelSchema with all $refs resolved
        """
        if definitions is None:
            definitions = self.definitions or {}
        if self.ref is not None:
            if self.ref.startswith("#/definitions/"):
                def_name = self.ref.split("/")[-1]
                if def_name in definitions:
                    resolved = definitions[def_name].resolve_refs(definitions)
                    if not resolved.title:
                        resolved.title = def_name
                    return resolved
            elif "#/" in self.ref:
                model_name = self.ref.split("#/")[-1]
                if model_name in definitions:
                    resolved_schema = definitions[model_name].resolve_refs(definitions)
                    if not resolved_schema.title:
                        resolved_schema.title = model_name
                    return resolved_schema
            elif "#" in self.ref and (not self.ref.startswith("#")):
                model_name = self.ref.split("#")[-1]
                if model_name in definitions:
                    resolved_schema = definitions[model_name].resolve_refs(definitions)
                    if not resolved_schema.title:
                        resolved_schema.title = model_name
                    return resolved_schema
            elif any(
                (
                    schema_file in self.ref
                    for schema_file in [
                        "semver_model.schema.yaml",
                        "onex_field_model.schema.yaml",
                    ]
                )
            ):
                if "semver_model" in self.ref:
                    return ModelSchema(type="object", title="ModelSemVer")
                if "onex_field_model" in self.ref:
                    return ModelSchema(type="object", title="ModelOnexField")
            msg = f"FAIL_FAST: Unresolved schema reference: {self.ref}. Available definitions: {list[Any](definitions.keys())}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        resolved = self.model_copy(deep=True)
        if resolved.properties:
            resolved_props = {}
            for name, prop in resolved.properties.items():
                resolved_props[name] = prop.resolve_refs(definitions)
            resolved.properties = resolved_props
        if resolved.items:
            resolved.items = resolved.items.resolve_refs(definitions)
        if resolved.definitions:
            resolved_defs = {}
            for name, definition in resolved.definitions.items():
                resolved_defs[name] = definition.resolve_refs(definitions)
            resolved.definitions = resolved_defs
        if resolved.all_of:
            resolved.all_of = [
                schema.resolve_refs(definitions) for schema in resolved.all_of
            ]
        if resolved.any_of:
            resolved.any_of = [
                schema.resolve_refs(definitions) for schema in resolved.any_of
            ]
        if resolved.one_of:
            resolved.one_of = [
                schema.resolve_refs(definitions) for schema in resolved.one_of
            ]
        return resolved

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON Schema format."""
        schema: dict[str, Any] = {"type": self.schema_type}
        if (
            self.definitions is not None
            or self.all_of is not None
            or self.any_of is not None
            or (self.one_of is not None)
        ):
            schema["$schema"] = f"http://json-schema.org/{self.schema_version}/schema#"
        if self.title:
            schema["title"] = self.title
        if self.description:
            schema["description"] = self.description
        if self.ref:
            schema["$ref"] = self.ref
        if self.enum_values:
            schema["enum"] = self.enum_values
        if self.pattern:
            schema["pattern"] = self.pattern
        if self.format:
            schema["format"] = self.format
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        if self.multiple_of is not None:
            schema["multipleOf"] = self.multiple_of
        if self.items:
            schema["items"] = self.items.to_dict()
        if self.min_items is not None:
            schema["minItems"] = self.min_items
        if self.max_items is not None:
            schema["maxItems"] = self.max_items
        if self.unique_items is not None:
            schema["uniqueItems"] = self.unique_items
        if self.properties:
            schema["properties"] = {
                name: prop.to_dict() for name, prop in self.properties.items()
            }
        if self.required:
            schema["required"] = self.required
        if self.additional_properties is not None:
            schema["additionalProperties"] = self.additional_properties
        if self.min_properties is not None:
            schema["minProperties"] = self.min_properties
        if self.max_properties is not None:
            schema["maxProperties"] = self.max_properties
        if self.nullable:
            schema["nullable"] = self.nullable
        if self.default_value is not None:
            schema["default"] = self.default_value.to_value()
        if self.definitions:
            schema["definitions"] = {
                name: definition.to_dict()
                for name, definition in self.definitions.items()
            }
        if self.all_of:
            schema["allOf"] = [s.to_dict() for s in self.all_of]
        if self.any_of:
            schema["anyOf"] = [s.to_dict() for s in self.any_of]
        if self.one_of:
            schema["oneOf"] = [s.to_dict() for s in self.one_of]
        if self.examples:
            schema["examples"] = self.examples
        return schema

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Optional["ModelSchema"]:
        """Create from JSON Schema dict[str, Any]ionary."""
        if data is None:
            return None
        properties = None
        if "properties" in data and isinstance(data["properties"], dict):
            properties = {}
            for name, prop_data in data["properties"].items():
                if isinstance(prop_data, dict):
                    properties[name] = cls.from_dict(prop_data)
        items = None
        if "items" in data and isinstance(data["items"], dict):
            items = cls.from_dict(data["items"])
        definitions = None
        if "definitions" in data and isinstance(data["definitions"], dict):
            definitions = {}
            for name, def_data in data["definitions"].items():
                if isinstance(def_data, dict):
                    definitions[name] = cls.from_dict(def_data)
        all_of = None
        if "allOf" in data and isinstance(data["allOf"], list):
            all_of = [
                cls.from_dict(schema_data)
                for schema_data in data["allOf"]
                if schema_data
            ]
        any_of = None
        if "anyOf" in data and isinstance(data["anyOf"], list):
            any_of = [
                cls.from_dict(schema_data)
                for schema_data in data["anyOf"]
                if schema_data
            ]
        one_of = None
        if "oneOf" in data and isinstance(data["oneOf"], list):
            one_of = [
                cls.from_dict(schema_data)
                for schema_data in data["oneOf"]
                if schema_data
            ]
        schema_version = "draft-07"
        if "$schema" in data and isinstance(data["$schema"], str):
            try:
                schema_version = data["$schema"].split("/")[-2]
            except (IndexError, AttributeError):
                schema_version = "draft-07"
        examples = None
        if "examples" in data:
            examples_data = data["examples"]
            if isinstance(examples_data, list):
                examples = []
                for example in examples_data:
                    if isinstance(example, str):
                        examples.append(
                            ModelExample(
                                name=example, description=f"Example: {example}"
                            )
                        )
                    elif isinstance(example, dict):
                        examples.append(ModelExample.model_validate(example))
            elif isinstance(examples_data, str | int | float | bool):
                examples = [
                    ModelExample(
                        name=str(examples_data), description=f"Example: {examples_data}"
                    )
                ]
        from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
        from omnibase_core.logging.structured import (
            emit_log_event_sync as emit_log_event,
        )

        if data.get("type") == "string" and data.get("format"):
            emit_log_event(
                LogLevel.INFO,
                "ModelSchema.from_dict: parsing string with format",
                {
                    "type": data.get("type"),
                    "format": data.get("format"),
                    "description": data.get("description", "")[:50],
                },
            )
        parsed_version = (
            parse_semver_from_string(schema_version)
            if isinstance(schema_version, str)
            else schema_version
        )
        version_str = (
            str(parsed_version)
            if hasattr(parsed_version, "__str__")
            else schema_version
        )
        return cls(
            type=data.get("type", "object"),
            schema_version=version_str if isinstance(version_str, str) else "draft-07",
            title=data.get("title"),
            description=data.get("description"),
            **{"$ref": data.get("$ref")} if data.get("$ref") else {},
            enum=data.get("enum"),
            pattern=data.get("pattern"),
            format=data.get("format"),
            minLength=data.get("minLength"),
            maxLength=data.get("maxLength"),
            minimum=data.get("minimum"),
            maximum=data.get("maximum"),
            multiple_of=data.get("multipleOf"),
            items=items,
            min_items=data.get("minItems"),
            max_items=data.get("maxItems"),
            unique_items=data.get("uniqueItems"),
            properties=(
                {k: v for k, v in properties.items() if v is not None}
                if properties
                else None
            ),
            required=data.get("required"),
            additional_properties=data.get("additionalProperties", True),
            min_properties=data.get("minProperties"),
            max_properties=data.get("maxProperties"),
            nullable=data.get("nullable", False),
            default_value=(
                ModelSchemaValue.from_value(data.get("default"))
                if data.get("default") is not None
                else None
            ),
            definitions=(
                {k: v for k, v in definitions.items() if v is not None}
                if definitions
                else None
            ),
            all_of=[s for s in all_of if s is not None] if all_of else None,
            any_of=[s for s in any_of if s is not None] if any_of else None,
            one_of=[s for s in one_of if s is not None] if one_of else None,
            examples=examples,
        )


SchemaModel = ModelSchema
