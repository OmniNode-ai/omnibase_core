"""
Type alias for JSON-serializable values.

Represents values that can be serialized to JSON by Pydantic's model_dump().
"""

from typing import Any

# SerializableValue represents JSON-compatible values
# We use Any here because:
# 1. Recursive type aliases cause Pydantic schema generation issues
# 2. This type is primarily used for documentation and type hints
# 3. Pydantic's model_dump() guarantees JSON-serializable output
# The @allow_dict_any decorator should NOT be applied to these types
# as they represent legitimate uses of Any for serialization.
SerializableValue = Any

# SerializedDict represents the output of Pydantic's model_dump()
SerializedDict = dict[str, SerializableValue]


__all__ = ["SerializableValue", "SerializedDict"]
