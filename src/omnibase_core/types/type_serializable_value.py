"""
Type aliases for JSON-serializable values.

This module provides type aliases for values that can be serialized to JSON,
used throughout the codebase for Pydantic model serialization, API payloads,
and configuration data.

Type Aliases:
    SerializableValue: A JSON-compatible value type (recursive). Equivalent to
        ``JsonType`` from ``type_json.py`` - supports primitives (str, int, float,
        bool, None) and nested lists/dicts.

    SerializedDict: A dictionary with string keys and JSON-serializable values.
        Represents the output of ``Pydantic.model_dump()``.

Design Decision:
    This module re-exports ``JsonType`` as ``SerializableValue`` for semantic clarity
    in contexts that deal specifically with serialization (e.g., model_dump() output,
    API responses). While technically the same type, the name ``SerializableValue``
    better communicates the intent in these contexts.

    The PEP 695 ``type`` statement used in ``JsonType`` properly handles recursive
    type definitions without causing RecursionError in Pydantic's schema generation,
    which was the original motivation for using ``Any``.

Thread Safety:
    These are type aliases only (no runtime state). Safe for concurrent access.

Example:
    >>> from omnibase_core.types.type_serializable_value import (
    ...     SerializableValue,
    ...     SerializedDict,
    ... )
    >>>
    >>> # Type-safe nested JSON structures
    >>> def process_data(data: SerializableValue) -> SerializedDict:
    ...     if isinstance(data, dict):
    ...         return data
    ...     return {"value": data}
    >>>
    >>> # Works with Pydantic model_dump() output
    >>> from pydantic import BaseModel
    >>> class MyModel(BaseModel):
    ...     name: str
    >>> model = MyModel(name="test")
    >>> serialized: SerializedDict = model.model_dump()

See Also:
    - ``omnibase_core.types.type_json``: Core JSON type definitions
    - ``omnibase_core.types.type_json.JsonType``: The underlying recursive type
    - ``omnibase_core.types.type_json.JsonPrimitive``: Scalar JSON values only
"""

from omnibase_core.types.type_json import JsonType

# SerializableValue represents JSON-compatible values (str, int, float, bool, None,
# list, dict) that can be serialized by Pydantic's model_dump().
#
# This is a re-export of JsonType for semantic clarity in serialization contexts.
# JsonType uses PEP 695 `type` statement which properly handles recursive types
# without RecursionError in Pydantic's schema generation.
#
# Type structure (from JsonType):
#     JsonPrimitive | list[JsonType] | dict[str, JsonType]
#
# Where JsonPrimitive = str | int | float | bool | None
SerializableValue = JsonType

# SerializedDict represents the output of Pydantic's model_dump().
# Keys are strings, values are JSON-serializable (see SerializableValue/JsonType).
#
# Common use cases:
# - Pydantic model serialization: model.model_dump() -> SerializedDict
# - API response payloads
# - Configuration data storage
# - Event envelope payloads (see ModelOnexEnvelope)
SerializedDict = dict[str, JsonType]


__all__ = ["SerializableValue", "SerializedDict"]
