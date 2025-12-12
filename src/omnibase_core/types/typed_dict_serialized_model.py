"""
TypedDictSerializedModel.

Type-safe dictionary for serialized Pydantic model output.
This TypedDict represents the output of model_dump() calls.
"""

from omnibase_core.types.type_serializable_value import SerializedDict

# Re-export SerializedDict as the primary type for serialize() methods
# This is the return type of model_dump() and provides type safety
# while still allowing arbitrary string keys
TypedDictSerializedModel = SerializedDict


__all__ = ["TypedDictSerializedModel"]
