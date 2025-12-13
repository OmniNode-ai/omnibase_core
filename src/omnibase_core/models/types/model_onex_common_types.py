"""
ONEX Common Type Definitions

Centralized type aliases for consistent typing across the ONEX codebase.
Replaces Any types with specific, constrained alternatives.

ARCHITECTURAL PRINCIPLE: Strong Typing Only
- NO Any types - always use specific typed alternatives
- NO loose Union fallbacks - choose one type and stick to it
- NO "convenience" conversion methods - use proper types from the start

DEPRECATION NOTICE - JsonSerializable:
The JsonSerializable type alias is deprecated. It provides no real validation
and is essentially a type-hinted Any. Instead:

1. For extension/metadata values, use ModelExtensionData (proper Pydantic model)
2. For specific use cases, use the more constrained type aliases below
3. For new code, always define a proper Pydantic model with validation

Migration Examples:
    OLD: value: JsonSerializable
    NEW: value: PropertyValue  # For simple key-value data
    NEW: value: MetadataValue  # For metadata
    NEW: value: ModelExtensionData  # For extensions (preferred)
"""

from __future__ import annotations

from typing import Any

# DEPRECATED: JsonSerializable - Do not use in new code
# JSON-serializable value types (most common replacement for Any)
# Recursive type alias for JSON-compatible data structures
#
# WARNING: This type alias provides no validation and should be replaced
# with proper Pydantic models or more specific type aliases below.
JsonSerializable = (
    str
    | int
    | float
    | bool
    | list[Any]  # Cannot be fully recursive in Python 3.11
    | dict[str, Any]  # Cannot be fully recursive in Python 3.11
    | None
)

# Property/metadata values (for generic containers)
PropertyValue = str | int | float | bool | list[str] | dict[str, str]

# Environment variable values
EnvValue = str | int | float | bool | None

# Metadata/result values (allows nested structures)
MetadataValue = str | int | float | bool | list[str] | dict[str, str] | None

# Validation field values (for validation errors)
# Recursive type alias for validation error contexts
# Using PEP 695 type statement to avoid RecursionError with Pydantic
type ValidationValue = (
    str | int | float | bool | list[ValidationValue] | dict[str, ValidationValue] | None
)

# Configuration values (for config models)
ConfigValue = str | int | float | bool | list[str] | dict[str, str] | None

# CLI/argument values (for command line processing)
CliValue = str | int | float | bool | list[str]

# Tool/service parameter values (same as PropertyValue for consistency)
ParameterValue = PropertyValue

# Result/output values (for result models)
# Recursive type alias for result/output data
# Using PEP 695 type statement to avoid RecursionError with Pydantic
type ResultValue = (
    str | int | float | bool | list[ResultValue] | dict[str, ResultValue] | None
)

# ONEX Type Safety Guidelines:
#
# When replacing Any types:
# 1. Choose the most specific type alias that fits the use case
# 2. Prefer JsonSerializable for general data interchange
# 3. Use PropertyValue for key-value stores and property containers
# 4. Use MetadataValue for metadata and context information
# 5. Use ValidationValue for validation error contexts
# 6. Create new specific aliases rather than reusing generic ones
#
# Avoid these patterns:
# ❌ field: Any = Field(...)
# ❌ **kwargs: Any
# ❌ def method(value: Any) -> Any:
# ❌ str | int | Any  # Any defeats the purpose
# ❌ from typing import Union, , Any  # Use modern syntax, Any
#
# Prefer these patterns:
# ✅ field: JsonSerializable = Field(...)
# ✅ **kwargs: str  # or specific type
# ✅ def method(value: PropertyValue) -> PropertyValue:
# ✅ str | int | float | bool  # specific alternatives only
# ✅ type JsonSerializable = ... | list[JsonSerializable]  # PEP 695 recursive type statement (Python 3.12+)
