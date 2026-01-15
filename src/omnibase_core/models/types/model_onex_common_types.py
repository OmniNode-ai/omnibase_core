"""
ONEX Common Type Definitions

Centralized type aliases for consistent typing across the ONEX codebase.
Replaces Any types with specific, constrained alternatives.

ARCHITECTURAL PRINCIPLE: Strong Typing Only
- NO Any types - always use specific typed alternatives
- NO loose Union fallbacks - choose one type and stick to it
- NO "convenience" conversion methods - use proper types from the start

For JSON-serializable data:
- Use JsonSerializable from omnibase_core.models.types (proper PEP 695 recursive type)
- For specific use cases, use the more constrained type aliases below
- For new code, prefer Pydantic models with validation when structure is known
"""

from __future__ import annotations

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

# NOTE: Narrower variants exist for specific use cases:
# - QueryParameterValue (model_query_parameters.py): URL query strings (allows None, no dict)
# - ScalarConfigValue (model_config_types.py): simple scalars only (no list, dict, or None)

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
# 2. Use JsonSerializable (from omnibase_core.models.types) for general data interchange
# 3. Use PropertyValue for key-value stores and property containers
# 4. Use MetadataValue for metadata and context information
# 5. Use ValidationValue for validation error contexts
# 6. Create new specific aliases rather than reusing generic ones
#
# Avoid these patterns:
# - field: Any = Field(...)
# - **kwargs: Any
# - def method(value: Any) -> Any:
# - str | int | Any  # Any defeats the purpose
#
# Prefer these patterns:
# - field: JsonSerializable = Field(...)  # from omnibase_core.models.types
# - **kwargs: str  # or specific type
# - def method(value: PropertyValue) -> PropertyValue:
# - str | int | float | bool  # specific alternatives only
