"""
Type alias for JSON-serializable values.

Represents values that can be serialized to JSON by Pydantic's model_dump().
"""

from typing import Any

# SerializableValue represents JSON-compatible values (str, int, float, bool, None,
# list, dict) that can be serialized by Pydantic's model_dump().
#
# We use `Any` here because recursive type aliases like:
#   SerializableValue = str | int | ... | dict[str, "SerializableValue"]
# cause RecursionError in Pydantic's schema generation.
#
# This is an intentional use of Any for JSON serialization compatibility.
# The actual type at runtime is constrained to JSON-serializable types by
# Pydantic's model_dump() which guarantees valid JSON output.
#
# Semantic meaning: str | int | float | bool | None | list | dict (nested)
SerializableValue = Any

# SerializedDict represents the output of Pydantic's model_dump().
# Keys are strings, values are JSON-serializable (see SerializableValue).
SerializedDict = dict[str, SerializableValue]


__all__ = ["SerializableValue", "SerializedDict"]
