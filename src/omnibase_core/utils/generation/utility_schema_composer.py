"""
Schema Composer Utility for ONEX Contract Generation.

Handles composition and merging of schemas with external references.
Resolves $ref references by loading and merging external schema content.
"""

import copy
from pathlib import Path
from typing import Any

from omnibase.protocols.types import LogLevel

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.utils.generation.utility_schema_loader import UtilitySchemaLoader


class UtilitySchemaComposer:
    """
    Utility for composing schemas by resolving and merging external references.

    Handles:
    - Resolving $ref references to external schema files
    - Merging properties from external schemas
    - Combining required field lists
    - Detecting and preventing circular references
    - Recursive resolution of nested references
    """

    def __init__(self, schema_loader: UtilitySchemaLoader | None = None):
        """
        Initialize the schema composer.

        Args:
            schema_loader: Schema loader utility for loading external files
        """
        self.schema_loader = schema_loader or UtilitySchemaLoader()
        self._resolution_stack: set[str] = set()  # Track circular references

    def compose_contract_definitions(
        self,
        contract_data: dict[str, Any],
        contract_path: Path,
    ) -> dict[str, dict[str, Any]]:
        """
        Compose all definitions in a contract by resolving external references.

        Args:
            contract_data: Full contract data dictionary
            contract_path: Path to the contract file (for relative reference resolution)

        Returns:
            Dictionary of fully composed definitions with resolved references
        """
        definitions = contract_data.get("definitions", {})
        contract_dir = contract_path.parent

        emit_log_event(
            LogLevel.INFO,
            f"Composing contract definitions from {contract_path}",
            {
                "contract_path": str(contract_path),
                "definitions_count": len(definitions),
                "definition_names": list(definitions.keys()),
            },
        )

        composed_definitions = {}

        for def_name, def_schema in definitions.items():
            emit_log_event(
                LogLevel.DEBUG,
                f"Composing definition: {def_name}",
                {"definition_name": def_name},
            )

            try:
                composed_schema = self.compose_schema(
                    def_schema,
                    contract_dir,
                    def_name,
                )
                composed_definitions[def_name] = composed_schema

                emit_log_event(
                    LogLevel.DEBUG,
                    f"Successfully composed definition: {def_name}",
                    {
                        "definition_name": def_name,
                        "has_properties": "properties" in composed_schema,
                        "properties_count": len(composed_schema.get("properties", {})),
                        "has_required": "required" in composed_schema,
                        "required_count": len(composed_schema.get("required", [])),
                    },
                )

            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Failed to compose definition: {def_name}",
                    {
                        "definition_name": def_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                # Keep original schema as fallback
                composed_definitions[def_name] = def_schema

        return composed_definitions

    def compose_schema(
        self,
        schema: dict[str, Any],
        base_dir: Path,
        context_name: str = "unknown",
    ) -> dict[str, Any]:
        """
        Compose a single schema by resolving any $ref references.

        Args:
            schema: Schema definition to compose
            base_dir: Base directory for resolving relative references
            context_name: Name for logging/debugging context

        Returns:
            Fully composed schema with resolved references
        """
        # Check for circular reference
        if context_name in self._resolution_stack:
            msg = f"Circular reference detected: {context_name}"
            raise ValueError(msg)

        # If no $ref, return as-is (but recursively process nested schemas)
        if "$ref" not in schema:
            return self._process_nested_schemas(schema, base_dir)

        ref_path = schema["$ref"]
        emit_log_event(
            LogLevel.DEBUG,
            f"Resolving reference: {ref_path}",
            {"ref_path": ref_path, "context": context_name},
        )

        # Add to resolution stack
        self._resolution_stack.add(context_name)

        try:
            # Parse the reference
            if "#" in ref_path:
                file_path, fragment = ref_path.split("#", 1)
                fragment = "#" + fragment if fragment else "#/"
            else:
                file_path = ref_path
                fragment = "#/"

            # Resolve and load the external schema
            resolved_path = self.schema_loader.resolve_schema_path(file_path, base_dir)
            external_schema = self.schema_loader.load_schema(
                str(resolved_path),
                base_dir,
            )

            # Extract the specific fragment
            if fragment and fragment != "#/":
                external_schema = self.schema_loader.extract_schema_fragment(
                    external_schema,
                    fragment,
                )

            # Recursively compose the external schema
            composed_external = self.compose_schema(
                external_schema,
                base_dir,
                f"{context_name}->external",
            )

            # Merge with any additional properties in the current schema
            merged_schema = self._merge_schemas(composed_external, schema)

            emit_log_event(
                LogLevel.DEBUG,
                f"Successfully resolved reference: {ref_path}",
                {
                    "ref_path": ref_path,
                    "context": context_name,
                    "external_properties": len(composed_external.get("properties", {})),
                    "merged_properties": len(merged_schema.get("properties", {})),
                },
            )

            return merged_schema

        finally:
            # Remove from resolution stack
            self._resolution_stack.discard(context_name)

    def _process_nested_schemas(
        self,
        schema: dict[str, Any],
        base_dir: Path,
    ) -> dict[str, Any]:
        """
        Process nested schemas within a schema definition.

        Args:
            schema: Schema to process
            base_dir: Base directory for reference resolution

        Returns:
            Schema with all nested references resolved
        """
        result = copy.deepcopy(schema)

        # Process properties
        if "properties" in result:
            for prop_name, prop_schema in result["properties"].items():
                if isinstance(prop_schema, dict):
                    result["properties"][prop_name] = self.compose_schema(
                        prop_schema,
                        base_dir,
                        f"property:{prop_name}",
                    )

        # Process array items
        if "items" in result and isinstance(result["items"], dict):
            result["items"] = self.compose_schema(
                result["items"],
                base_dir,
                "array_items",
            )

        # Process additional properties
        if "additionalProperties" in result and isinstance(
            result["additionalProperties"],
            dict,
        ):
            result["additionalProperties"] = self.compose_schema(
                result["additionalProperties"],
                base_dir,
                "additional_properties",
            )

        return result

    def _merge_schemas(
        self,
        base_schema: dict[str, Any],
        overlay_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Merge two schemas, with overlay taking precedence.

        Args:
            base_schema: Base schema (typically from external reference)
            overlay_schema: Overlay schema (from current definition)

        Returns:
            Merged schema
        """
        result = copy.deepcopy(base_schema)

        for key, value in overlay_schema.items():
            if key == "$ref":
                # Skip $ref in overlay - it was already resolved
                continue
            if key == "properties" and "properties" in result:
                # Merge properties
                result["properties"].update(value)
            elif key == "required" and "required" in result:
                # Merge required arrays, avoiding duplicates
                existing_required = set(result["required"])
                new_required = set(value)
                result["required"] = list(existing_required | new_required)
            else:
                # Override other fields
                result[key] = value

        return result

    def validate_composed_schema(
        self,
        schema: dict[str, Any],
        schema_name: str,
    ) -> list[str]:
        """
        Validate a composed schema for common issues.

        Args:
            schema: Composed schema to validate
            schema_name: Name of the schema for error reporting

        Returns:
            List of validation warnings/errors
        """
        issues = []

        # Check for empty object schemas
        if schema.get("type") == "object" and not schema.get("properties"):
            issues.append(f"Object schema '{schema_name}' has no properties")

        # Check for required fields that don't exist in properties
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for field in required:
            if field not in properties:
                issues.append(
                    f"Required field '{field}' not found in properties of '{schema_name}'",
                )

        # Check for properties with no type
        for prop_name, prop_schema in properties.items():
            if (
                isinstance(prop_schema, dict)
                and "type" not in prop_schema
                and "$ref" not in prop_schema
            ):
                issues.append(
                    f"Property '{prop_name}' in '{schema_name}' has no type definition",
                )

        return issues

    def clear_resolution_stack(self):
        """Clear the resolution stack (useful for testing)."""
        self._resolution_stack.clear()
