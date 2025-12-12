"""
TypedDictAdditionalFields.

Type-safe dictionary for additional/extensible fields in models.
"""

from omnibase_core.types.type_serializable_value import SerializableValue

# Type alias for additional fields dictionaries
# This replaces dict[str, Any] for extensible field containers
TypedDictAdditionalFields = dict[str, SerializableValue]


__all__ = ["TypedDictAdditionalFields"]
