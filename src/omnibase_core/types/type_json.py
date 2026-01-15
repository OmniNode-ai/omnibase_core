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
    JsonType: Recursive type for full JSON structure with proper nesting (PEP 695)

Design Decisions:
    - Uses PEP 604 syntax (X | Y) instead of Union[X, Y] for modern Python 3.12+
    - JsonType uses PEP 695 ``type`` statement for proper recursive definition
    - Separate PrimitiveValue (without None) for non-nullable contexts

Usage:
    >>> from omnibase_core.types.type_json import (
    ...     JsonPrimitive,
    ...     JsonType,
    ...     PrimitiveValue,
    ...     ToolParameterValue,
    ... )
    >>>
    >>> # Use in function signatures
    >>> def process_json(data: JsonType) -> JsonType:
    ...     pass
    >>>
    >>> # Use for configuration values
    >>> config: dict[str, JsonType] = {"key": "value", "count": 42}
    >>>
    >>> # Use for tool parameters with constrained types
    >>> params: dict[str, ToolParameterValue] = {"name": "test", "tags": ["a", "b"]}

See Also:
    - omnibase_core.types.type_effect_result: Effect-specific type aliases
    - omnibase_core.utils.compute_transformations: JSON transformation utilities
    - docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md: Node architecture patterns
"""

from datetime import datetime
from uuid import UUID

__all__ = [
    "JsonPrimitive",
    "JsonType",
    "PrimitiveValue",
    "PrimitiveContainer",
    "StrictJsonPrimitive",
    "StrictJsonType",
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
# - UUID: UUID objects (Pydantic's model_dump() preserves these by default)
# - datetime: datetime objects (Pydantic's model_dump() preserves these by default)
#
# Note: UUID and datetime are included because Pydantic's default serialization
# behavior (model_dump()) preserves these types. Including them ensures that
# JsonType can properly type nested structures that contain Pydantic model data.
#
# Example:
#     >>> value: JsonPrimitive = "hello"
#     >>> value: JsonPrimitive = 42
#     >>> value: JsonPrimitive = None
#     >>> value: JsonPrimitive = UUID("...")
#     >>> value: JsonPrimitive = datetime.now()
JsonPrimitive = str | int | float | bool | None | UUID | datetime


# Type alias for core non-nullable primitive values.
# Contains the fundamental JSON primitives (str, int, float, bool) without None.
#
# Note: This is a subset of JsonPrimitive. JsonPrimitive extends this with
# None, UUID, and datetime for Pydantic compatibility.
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
# JSON Type (Recursive - PEP 695)
# ==============================================================================

# PEP 695 recursive type alias (Python 3.12+)
# Pydantic 2.x requires this syntax for recursive types to avoid RecursionError.
#
# JsonType represents any JSON-serializable value:
#   - Primitives: str, int, float, bool, None
#   - Containers: list of JsonType, dict mapping str to JsonType
#
# This type is recursive, meaning:
# - dict values can themselves be JsonType
# - list elements can themselves be JsonType
#
# Use this when you need:
# - Full type coverage for deeply nested JSON
# - Type checking of nested structures
# - JSON schema validation contexts
# - Requirement values in capability matching
#
# Examples of valid values:
#   True                                    # bool
#   20                                      # int
#   0.95                                    # float
#   "us-east-1"                             # str
#   None                                    # null
#   ["postgres", "mysql"]                   # list
#   {"timeout": 30, "retries": 3}           # nested dict
#
# Example usage:
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
type JsonType = JsonPrimitive | list[JsonType] | dict[str, JsonType]


# ==============================================================================
# Strict JSON Types (RFC 8259 Compliant)
# ==============================================================================

# Type alias for STRICT JSON primitive (scalar) values.
# These are the only primitive types allowed in RFC 8259 JSON:
#   - str: JSON string
#   - int: JSON integer number
#   - float: JSON floating-point number (finite values only at runtime)
#   - bool: JSON boolean (true/false)
#   - None: JSON null
#
# IMPORTANT: This differs from JsonPrimitive which includes UUID and datetime
# for Pydantic model_dump() compatibility. StrictJsonPrimitive is for contexts
# where values MUST be directly JSON-serializable without any conversion.
#
# Use StrictJsonPrimitive when:
#   - Data will be passed to json.dumps() directly
#   - Data crosses service boundaries (APIs, message queues)
#   - Data is stored in JSON columns (PostgreSQL JSONB, etc.)
#   - Strict RFC 8259 compliance is required
#
# Use JsonPrimitive when:
#   - Working with Pydantic model_dump() output
#   - Internal data structures that won't be serialized directly
#   - Type flexibility is acceptable
#
# Example:
#     >>> value: StrictJsonPrimitive = "hello"   # Valid
#     >>> value: StrictJsonPrimitive = 42        # Valid
#     >>> value: StrictJsonPrimitive = None      # Valid
#     >>> value: StrictJsonPrimitive = UUID(...) # Type error - use str(uuid)
#     >>> value: StrictJsonPrimitive = datetime.now()  # Type error - use .isoformat()
StrictJsonPrimitive = str | int | float | bool | None


# PEP 695 recursive type alias for STRICT JSON values (Python 3.12+).
# This type represents any value that can be directly serialized to JSON
# per RFC 8259 without any type coercion or conversion.
#
# StrictJsonType is the type-safe counterpart to runtime JSON validation.
# When a field is typed as StrictJsonType, the static type system enforces
# the same constraints that runtime validators check.
#
# IMPORTANT: This differs from JsonType which allows UUID and datetime.
# StrictJsonType should be used when runtime validation rejects those types.
#
# Valid values:
#   - Primitives: str, int, float, bool, None
#   - Arrays: list of StrictJsonType
#   - Objects: dict with str keys and StrictJsonType values
#
# Invalid values (use JsonType instead if needed):
#   - UUID objects (convert with str(uuid))
#   - datetime objects (convert with .isoformat())
#   - Path objects (convert with str(path))
#   - Custom objects (convert with .model_dump() or manual serialization)
#
# Use StrictJsonType when:
#   - Runtime validation rejects UUID/datetime (type-runtime alignment)
#   - Data must serialize to JSON without conversion
#   - Strict RFC 8259 compliance is required
#
# Example:
#     >>> # Strict JSON - no UUID/datetime allowed
#     >>> config: dict[str, StrictJsonType] = {
#     ...     "id": "550e8400-e29b-41d4-a716-446655440000",  # str, not UUID
#     ...     "timestamp": "2024-01-15T10:30:00Z",           # str, not datetime
#     ...     "settings": {"timeout": 30, "enabled": True},
#     ... }
type StrictJsonType = (
    StrictJsonPrimitive | list[StrictJsonType] | dict[str, StrictJsonType]
)


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
# NOTE: None is NOT included (unlike JsonPrimitive/JsonType).
# This type is for contexts where values must be present and non-null.
# Use JsonType if you need to allow None in containers.
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
# NOTE: This is intentionally more constrained than JsonType:
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
