"""
JSON-compatible type aliases for ONEX.

This module provides centralized type aliases for JSON-compatible values,
eliminating scattered inline union types throughout the codebase.

These type aliases follow ONEX patterns by:
1. Reducing inline union type duplication (anti-pattern: "primitive soup")
2. Providing semantic naming for common JSON-related types
3. Centralizing type definitions for easier maintenance and refactoring
4. Using modern PEP 604 union syntax (X | Y) for clarity

Type Hierarchy:
    JsonPrimitive: Basic JSON scalar values (str, int, float, bool, None)
    JsonValue: Any JSON-compatible value including containers
    JsonType: Recursive type for full JSON structure with proper nesting

Design Decisions:
    - Uses PEP 604 syntax (X | Y) instead of Union[X, Y] for modern Python 3.12+
    - JsonValue uses Any for container contents to avoid recursive complexity
    - JsonType uses forward reference for true recursive definition
    - Separate PrimitiveValue (without None) for non-nullable contexts

Usage:
    >>> from omnibase_core.types.json_types import (
    ...     JsonPrimitive,
    ...     JsonValue,
    ...     JsonType,
    ...     PrimitiveValue,
    ...     ToolParameterValue,
    ... )
    >>>
    >>> # Use in function signatures
    >>> def process_json(data: JsonValue) -> JsonType:
    ...     pass
    >>>
    >>> # Use for configuration values
    >>> config: dict[str, JsonValue] = {"key": "value", "count": 42}
    >>>
    >>> # Use for tool parameters with constrained types
    >>> params: dict[str, ToolParameterValue] = {"name": "test", "tags": ["a", "b"]}

See Also:
    - omnibase_core.types.type_effect_result: Effect-specific type aliases
    - omnibase_core.utils.compute_transformations: JSON transformation utilities
    - docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md: Node architecture patterns
"""

from typing import Any

__all__ = [
    "JsonPrimitive",
    "JsonValue",
    "JsonType",
    "PrimitiveValue",
    "PrimitiveContainer",
    "ToolParameterValue",
]

# ==============================================================================
# JSON Primitive Types
# ==============================================================================

# Type alias for JSON primitive (scalar) values.
# These are the basic building blocks of JSON that cannot contain other values.
#
# Used when you need to represent a single JSON-compatible scalar value:
# - str: JSON string
# - int: JSON integer number
# - float: JSON floating-point number
# - bool: JSON boolean (true/false)
# - None: JSON null
#
# Example:
#     >>> value: JsonPrimitive = "hello"
#     >>> value: JsonPrimitive = 42
#     >>> value: JsonPrimitive = None
JsonPrimitive = str | int | float | bool | None


# Type alias for non-nullable primitive values.
# Same as JsonPrimitive but excludes None for contexts where null is not valid.
#
# Used when a value must be present (non-nullable contexts):
# - Required configuration fields
# - Non-optional function parameters
# - Values that must have meaningful content
#
# Replaces inline unions like:
#     str | int | float | bool
#
# Example:
#     >>> value: PrimitiveValue = "hello"  # Valid
#     >>> value: PrimitiveValue = None     # Type error - None not allowed
PrimitiveValue = str | int | float | bool


# ==============================================================================
# JSON Value Types (Non-Recursive)
# ==============================================================================

# Type alias for JSON-compatible values including containers.
# This is the most commonly used type for JSON data where you need
# to accept any valid JSON value but don't need recursive type checking.
#
# Includes:
# - All JsonPrimitive types (str, int, float, bool, None)
# - list[Any]: JSON arrays (nested content not type-checked)
# - dict[str, Any]: JSON objects (nested content not type-checked)
#
# NOTE: Uses Any for container contents to avoid recursive type complexity.
# For full recursive type checking, use JsonType instead.
#
# Replaces inline unions like:
#     str | int | float | bool | list[Any] | dict[str, Any] | None
#
# Example:
#     >>> data: JsonValue = {"users": [{"name": "Alice", "age": 30}]}
#     >>> data: JsonValue = [1, 2, 3]
#     >>> data: JsonValue = "simple string"
JsonValue = str | int | float | bool | list[Any] | dict[str, Any] | None


# ==============================================================================
# JSON Type (Recursive)
# ==============================================================================

# Type alias for full recursive JSON structure.
# Provides proper nested type definition for complete JSON documents.
#
# This type is recursive, meaning:
# - dict values can themselves be JsonType
# - list elements can themselves be JsonType
#
# Use this when you need:
# - Full type coverage for deeply nested JSON
# - Type checking of nested structures
# - JSON schema validation contexts
#
# NOTE: The forward reference "JsonType" enables recursive definition.
# Mypy and other type checkers will properly resolve this recursion.
#
# Example:
#     >>> # Deeply nested structure is fully typed
#     >>> config: JsonType = {
#     ...     "database": {
#     ...         "hosts": ["host1", "host2"],
#     ...         "settings": {
#     ...             "timeout": 30,
#     ...             "retry": True
#     ...         }
#     ...     }
#     ... }
JsonType = dict[str, "JsonType"] | list["JsonType"] | str | int | float | bool | None


# ==============================================================================
# Primitive Container Types
# ==============================================================================

# Type alias for containers of primitive values.
# Used when you have a value that is either a primitive or a simple
# collection of primitives (no deep nesting).
#
# Includes:
# - All PrimitiveValue types (str, int, float, bool)
# - list[PrimitiveValue]: Flat list of primitives
# - dict[str, PrimitiveValue]: Flat dict mapping to primitives
#
# NOTE: None is NOT included (unlike JsonPrimitive/JsonValue).
# This type is for contexts where values must be present and non-null.
# Use JsonValue if you need to allow None in containers.
#
# Use cases:
# - Simple configuration values
# - Flat metadata structures
# - Parameters that don't need deep nesting
#
# Example:
#     >>> settings: PrimitiveContainer = {"timeout": 30, "enabled": True}
#     >>> tags: PrimitiveContainer = ["prod", "critical"]
#     >>> count: PrimitiveContainer = 42
#     >>> invalid: PrimitiveContainer = None  # Type error - None not allowed
PrimitiveContainer = PrimitiveValue | list[PrimitiveValue] | dict[str, PrimitiveValue]


# ==============================================================================
# Tool Parameter Types
# ==============================================================================

# Type alias for tool/function parameter values.
# A constrained subset of JSON types commonly used for tool invocation parameters.
#
# Includes:
# - str, int, float, bool: Basic parameter types
# - list[str]: String arrays (common for tags, options, etc.)
# - dict[str, str]: String-to-string mappings (headers, env vars, etc.)
#
# NOTE: This is intentionally more constrained than JsonValue:
# - No None (parameters should be explicit)
# - No arbitrary nested structures
# - List/dict values are strings only
#
# Use cases:
# - MCP tool parameters
# - CLI argument values
# - API request parameters
#
# Replaces inline unions like:
#     str | int | float | bool | list[str] | dict[str, str]
#
# Example:
#     >>> params: dict[str, ToolParameterValue] = {
#     ...     "url": "https://example.com",
#     ...     "timeout": 30,
#     ...     "headers": {"Authorization": "Bearer token"},
#     ...     "tags": ["api", "external"]
#     ... }
ToolParameterValue = str | int | float | bool | list[str] | dict[str, str]
