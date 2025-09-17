"""
Enum Generator Utility for ONEX Contract Generation.

Handles discovery and generation of enum classes from JSON Schema definitions.
Provides consistent enum generation across all ONEX tools.
"""

import ast
from dataclasses import dataclass
from typing import Any

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.core.model_schema import ModelSchema


@dataclass
class EnumInfo:
    """Information about a discovered enum."""

    name: str
    values: list[str]
    source_field: str
    source_schema: str | None = None


class UtilityEnumGenerator:
    """
    Utility for discovering and generating enum classes from schemas.

    Handles:
    - Recursive discovery of enum fields in schemas
    - Generation of enum class names from values
    - Creation of enum AST nodes
    - Deduplication of enum definitions
    """

    def __init__(self, ast_builder=None, type_mapper=None):
        """
        Initialize the enum generator.

        Args:
            ast_builder: AST builder utility for generating enum classes
            type_mapper: Type mapper utility for name generation
        """
        self.ast_builder = ast_builder
        self.type_mapper = type_mapper

    def discover_enums_from_contract(self, contract_data: Any) -> list[EnumInfo]:
        """
        Discover all enum definitions from a contract document.

        Args:
            contract_data: Contract document (ModelContractDocument or dict)

        Returns:
            List of discovered enum information
        """
        enum_schemas = {}

        # Handle ModelContractDocument
        if hasattr(contract_data, "input_state") and contract_data.input_state:
            self._collect_enum_schemas_from_model_schema(
                contract_data.input_state,
                enum_schemas,
                source_schema="input_state",
            )

        if hasattr(contract_data, "output_state") and contract_data.output_state:
            self._collect_enum_schemas_from_model_schema(
                contract_data.output_state,
                enum_schemas,
                source_schema="output_state",
            )

        if hasattr(contract_data, "definitions") and contract_data.definitions:
            emit_log_event(
                LogLevel.INFO,
                f"Checking {len(contract_data.definitions)} definitions for enums",
                {"definition_count": len(contract_data.definitions)},
            )
            for def_name, def_schema in contract_data.definitions.items():
                emit_log_event(
                    LogLevel.DEBUG,
                    f"Checking definition '{def_name}' for enum patterns",
                    {
                        "definition_name": def_name,
                        "has_enum": (
                            hasattr(def_schema, "enum") if def_schema else False
                        ),
                        "schema_type": (
                            getattr(def_schema, "type", "unknown")
                            if def_schema
                            else "none"
                        ),
                    },
                )
                self._collect_enum_schemas_from_model_schema(
                    def_schema,
                    enum_schemas,
                    source_schema=f"definitions.{def_name}",
                )

        # Handle dict-based contract data
        if isinstance(contract_data, dict):
            if "input_state" in contract_data:
                self._collect_enum_schemas_from_dict(
                    contract_data["input_state"],
                    enum_schemas,
                    source_schema="input_state",
                )

            if "output_state" in contract_data:
                self._collect_enum_schemas_from_dict(
                    contract_data["output_state"],
                    enum_schemas,
                    source_schema="output_state",
                )

            if "definitions" in contract_data:
                for def_name, def_schema in contract_data["definitions"].items():
                    self._collect_enum_schemas_from_dict(
                        def_schema,
                        enum_schemas,
                        source_schema=f"definitions.{def_name}",
                    )

        # Convert to EnumInfo objects
        enums = []
        for enum_name, info in enum_schemas.items():
            enum_info = EnumInfo(
                name=enum_name,
                values=info["values"],
                source_field=info["source_field"],
                source_schema=info["source_schema"],
            )
            enums.append(enum_info)

        return enums

    def generate_enum_classes(self, enum_infos: list[EnumInfo]) -> list[ast.ClassDef]:
        """
        Generate AST class definitions for enum info objects.

        Args:
            enum_infos: List of enum information objects

        Returns:
            List of AST ClassDef nodes for enum classes
        """
        enum_classes = []

        for enum_info in enum_infos:
            if self.ast_builder:
                enum_class = self.ast_builder.generate_enum_class(
                    enum_info.name,
                    enum_info.values,
                )
            else:
                # Fallback enum generation
                enum_class = self._generate_enum_class_fallback(
                    enum_info.name,
                    enum_info.values,
                )

            enum_classes.append(enum_class)

            emit_log_event(
                LogLevel.DEBUG,
                f"Generated enum class {enum_info.name}",
                {
                    "enum_name": enum_info.name,
                    "value_count": len(enum_info.values),
                    "source": enum_info.source_schema,
                },
            )

        return enum_classes

    def generate_enum_name_from_values(self, enum_values: list[str]) -> str:
        """
        Generate an enum class name from enum values.

        Args:
            enum_values: List of enum string values

        Returns:
            Generated enum class name
        """
        if self.type_mapper:
            return self.type_mapper.generate_enum_name_from_values(enum_values)

        # Fallback name generation
        if not enum_values:
            return "EnumGeneric"

        first_value = enum_values[0]
        if isinstance(first_value, str):
            # Replace hyphens with underscores first
            clean_value = first_value.replace("-", "_")

            if "_" in clean_value:
                # Handle snake_case values (including those that had hyphens)
                parts = clean_value.split("_")
                return "Enum" + "".join(word.capitalize() for word in parts)
            # Handle single word values
            return f"Enum{clean_value.capitalize()}"

        return "EnumGeneric"

    def generate_enum_name_from_schema(self, schema: dict | ModelSchema) -> str:
        """
        Generate enum class name from schema context.

        Args:
            schema: Schema definition (dict or ModelSchema)

        Returns:
            Generated enum class name
        """
        # Extract enum values from schema
        if isinstance(schema, ModelSchema):
            enum_values = schema.enum_values or []
        elif isinstance(schema, dict):
            enum_values = schema.get("enum", [])
        else:
            return "EnumGeneric"

        return self.generate_enum_name_from_values(enum_values)

    def deduplicate_enums(self, enum_infos: list[EnumInfo]) -> list[EnumInfo]:
        """
        Remove duplicate enum definitions based on values.

        Args:
            enum_infos: List of enum information objects

        Returns:
            Deduplicated list of enum information objects
        """
        seen_values = {}
        deduplicated = []

        for enum_info in enum_infos:
            # Create a hashable key from sorted values
            values_key = tuple(sorted(enum_info.values))

            if values_key not in seen_values:
                seen_values[values_key] = enum_info
                deduplicated.append(enum_info)
            else:
                # Log duplicate found
                existing = seen_values[values_key]
                emit_log_event(
                    LogLevel.DEBUG,
                    f"Duplicate enum found: {enum_info.name} matches {existing.name}",
                    {
                        "duplicate_name": enum_info.name,
                        "existing_name": existing.name,
                        "values": enum_info.values,
                    },
                )

        return deduplicated

    # Private helper methods

    def _collect_enum_schemas_from_model_schema(
        self,
        schema: ModelSchema,
        enum_schemas: dict[str, dict],
        source_schema: str = "unknown",
    ) -> None:
        """Collect enum schemas from a ModelSchema object."""
        if not schema:
            emit_log_event(
                LogLevel.DEBUG,
                f"Skipping null schema in {source_schema}",
                {"source_schema": source_schema},
            )
            return

        # Log what we're examining
        emit_log_event(
            LogLevel.DEBUG,
            f"Examining schema in {source_schema}",
            {
                "source_schema": source_schema,
                "schema_type": getattr(schema, "schema_type", "NO_TYPE"),
                "has_enum_values": hasattr(schema, "enum_values")
                and bool(schema.enum_values),
                "enum_values": getattr(schema, "enum_values", None),
                "properties_count": (
                    len(schema.properties)
                    if hasattr(schema, "properties") and schema.properties
                    else 0
                ),
            },
        )

        # Check if this schema itself is an enum
        if schema.schema_type == "string" and schema.enum_values:
            enum_name = self.generate_enum_name_from_values(schema.enum_values)

            # TRACE: Enum discovery in schema
            emit_log_event(
                LogLevel.DEBUG,
                f"🔍 TRACE: Found enum in schema '{source_schema}'",
                {
                    "original_source": source_schema,
                    "generated_name": enum_name,
                    "enum_values": schema.enum_values,
                    "schema_type": schema.schema_type,
                },
            )

            emit_log_event(
                LogLevel.INFO,
                f"Found enum '{enum_name}' in {source_schema}",
                {
                    "enum_name": enum_name,
                    "values": schema.enum_values,
                    "source_schema": source_schema,
                },
            )
            enum_schemas[enum_name] = {
                "values": schema.enum_values,
                "source_field": "root",
                "source_schema": source_schema,
            }

        # Check properties for nested enums
        if schema.properties:
            for field_name, field_schema in schema.properties.items():
                if field_schema.schema_type == "string" and field_schema.enum_values:
                    enum_name = self.generate_enum_name_from_values(
                        field_schema.enum_values,
                    )
                    enum_schemas[enum_name] = {
                        "values": field_schema.enum_values,
                        "source_field": field_name,
                        "source_schema": source_schema,
                    }

                # Recursively check nested objects
                if field_schema.schema_type == "object":
                    self._collect_enum_schemas_from_model_schema(
                        field_schema,
                        enum_schemas,
                        f"{source_schema}.{field_name}",
                    )
                elif field_schema.schema_type == "array" and field_schema.items:
                    self._collect_enum_schemas_from_model_schema(
                        field_schema.items,
                        enum_schemas,
                        f"{source_schema}.{field_name}[]",
                    )

    def _collect_enum_schemas_from_dict(
        self,
        schema: dict,
        enum_schemas: dict[str, dict],
        source_schema: str = "unknown",
    ) -> None:
        """Collect enum schemas from a dict-based schema definition."""
        if not isinstance(schema, dict):
            return

        # Check if this schema itself is an enum
        if schema.get("type") == "string" and "enum" in schema:
            enum_name = self.generate_enum_name_from_schema(schema)
            enum_schemas[enum_name] = {
                "values": schema["enum"],
                "source_field": "root",
                "source_schema": source_schema,
            }

        # Check properties for nested enums
        if "properties" in schema:
            for field_name, field_schema in schema["properties"].items():
                if field_schema.get("type") == "string" and "enum" in field_schema:
                    enum_name = self.generate_enum_name_from_schema(field_schema)
                    enum_schemas[enum_name] = {
                        "values": field_schema["enum"],
                        "source_field": field_name,
                        "source_schema": source_schema,
                    }

                # Recursively check nested objects
                if field_schema.get("type") == "object":
                    self._collect_enum_schemas_from_dict(
                        field_schema,
                        enum_schemas,
                        f"{source_schema}.{field_name}",
                    )
                elif field_schema.get("type") == "array" and "items" in field_schema:
                    self._collect_enum_schemas_from_dict(
                        field_schema["items"],
                        enum_schemas,
                        f"{source_schema}.{field_name}[]",
                    )

    def _generate_enum_class_fallback(
        self,
        class_name: str,
        enum_values: list[str],
    ) -> ast.ClassDef:
        """
        Fallback enum class generation when AST builder is not available.

        Args:
            class_name: Name of the enum class
            enum_values: List of enum values

        Returns:
            AST ClassDef node for the enum
        """
        # Create class with str and Enum as bases
        bases = [
            ast.Name(id="str", ctx=ast.Load()),
            ast.Name(id="Enum", ctx=ast.Load()),
        ]

        body = []

        # Add docstring
        docstring = f"{class_name} enumeration from contract definitions."
        body.append(ast.Expr(value=ast.Constant(value=docstring)))

        # Add enum values
        for enum_value in enum_values:
            attr_name = enum_value.upper().replace("-", "_").replace(" ", "_")
            assignment = ast.Assign(
                targets=[ast.Name(id=attr_name, ctx=ast.Store())],
                value=ast.Constant(value=enum_value),
            )
            body.append(assignment)

        # If no values, add pass
        if len(body) == 1:  # Only docstring
            body.append(ast.Pass())

        class_def = ast.ClassDef(
            name=class_name,
            bases=bases,
            keywords=[],
            decorator_list=[],
            body=body,
        )

        # Fix missing locations
        ast.fix_missing_locations(class_def)
        return class_def
