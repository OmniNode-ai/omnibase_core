"""
ONEX Common Type Definitions

Centralized type aliases for consistent typing across the ONEX codebase.
Replaces Any types with specific, constrained alternatives.

ARCHITECTURAL PRINCIPLE: Strong Typing Only
- NO Any types - always use specific typed alternatives
- NO loose Union fallbacks - choose one type and stick to it
- NO "convenience" conversion methods - use proper types from the start
"""

from typing import Union

# JSON-serializable value types (most common replacement for Any)
JsonSerializable = Union[str, int, float, bool, list, dict, None]

# Property/metadata values (for generic containers)
PropertyValue = Union[str, int, float, bool, list[str], dict[str, str]]

# Environment variable values
EnvValue = Union[str, int, float, bool, None]

# Metadata/result values (allows nested structures)
MetadataValue = Union[str, int, float, bool, list[str], dict[str, str], None]

# Validation field values (for validation errors)
ValidationValue = Union[str, int, float, bool, list, dict, None]

# Configuration values (for config models)
ConfigValue = Union[str, int, float, bool, list[str], dict[str, str], None]

# CLI/argument values (for command line processing)
CliValue = Union[str, int, float, bool, list[str]]

# Tool/service parameter values
ParameterValue = Union[str, int, float, bool, list[str], dict[str, str]]

# Result/output values (for result models)
ResultValue = Union[str, int, float, bool, list, dict, None]

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
# ❌ Union[str, int, Any]  # Any defeats the purpose
#
# Prefer these patterns:
# ✅ field: JsonSerializable = Field(...)
# ✅ **kwargs: str  # or specific type
# ✅ def method(value: PropertyValue) -> PropertyValue:
# ✅ Union[str, int, float, bool]  # specific alternatives only
