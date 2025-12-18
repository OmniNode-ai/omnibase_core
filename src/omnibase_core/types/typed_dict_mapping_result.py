"""TypedDictMappingResult.

TypedDict for mapping step results in compute pipeline execution.

This provides a type-safe alternative to dict[str, Any] for mapping
step outputs where values are resolved from path expressions.
"""

from __future__ import annotations

# Note: MappingResult values can be any type resolved from path expressions
# (strings, numbers, dicts, lists, objects, etc.)
# We use object as the value type since it's more specific than Any
# and indicates the values are runtime-determined from path resolution.

# Type alias for mapping result - values are path-resolved and can be any JSON-compatible type
MappingResultDict = dict[str, object]


__all__ = ["MappingResultDict"]
