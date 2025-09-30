"""
ONEX Common Type Definitions

Centralized type aliases for consistent typing across the ONEX codebase.
Replaces Any types with specific, constrained alternatives.

ARCHITECTURAL PRINCIPLE: Strong Typing Only
- NO Any types - always use specific typed alternatives
- NO loose Union fallbacks - choose one type and stick to it
- NO "convenience" conversion methods - use proper types from the start
"""

from __future__ import annotations

# JSON-serializable value types (most common replacement for Any)
# Uses PEP 695 type statement for recursive type alias
type JsonSerializable = str | int | float | bool | list[JsonSerializable] | dict[
    str,
    JsonSerializable,
] | None

# Property/metadata values (for generic containers)
PropertyValue = str | int | float | bool | list[str] | dict[str, str]

# Environment variable values
EnvValue = str | int | float | bool | None

# Metadata/result values (allows nested structures)
MetadataValue = str | int | float | bool | list[str] | dict[str, str] | None

# Validation field values (for validation errors)
# Uses PEP 695 type statement for recursive type alias
type ValidationValue = str | int | float | bool | list[ValidationValue] | dict[
    str,
    ValidationValue,
] | None

# Configuration values (for config models)
ConfigValue = str | int | float | bool | list[str] | dict[str, str] | None

# CLI/argument values (for command line processing)
CliValue = str | int | float | bool | list[str]

# Tool/service parameter values (same as PropertyValue for consistency)
ParameterValue = PropertyValue

# Result/output values (for result models)
# Uses PEP 695 type statement for recursive type alias
type ResultValue = str | int | float | bool | list[ResultValue] | dict[
    str,
    ResultValue,
] | None

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
# ❌ from typing import Union, Any  # Use modern syntax
#
# Prefer these patterns:
# ✅ field: JsonSerializable = Field(...)
# ✅ **kwargs: str  # or specific type
# ✅ def method(value: PropertyValue) -> PropertyValue:
# ✅ str | int | float | bool  # specific alternatives only
# ✅ type JsonSerializable = ... | list[JsonSerializable]  # PEP 695 recursive type aliases
