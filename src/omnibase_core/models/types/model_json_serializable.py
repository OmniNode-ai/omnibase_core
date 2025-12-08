"""
JSON-serializable type definition using PEP 695 type statement.

This module provides the JsonSerializable recursive type alias that represents
all valid JSON values as defined by RFC 8259. This enables type-safe handling
of data that must be JSON-compatible.

Design Notes:
    This module uses Python 3.12+ PEP 695 syntax (``type X = ...``) for the
    recursive type definition. For the non-recursive version exported from
    the package, see ``omnibase_core.models.types.model_onex_common_types``.

JSON Value Types (RFC 8259):
    - string: Represented as ``str``
    - number: Represented as ``int`` or ``float``
    - boolean: Represented as ``bool``
    - null: Represented as ``None``
    - object: Represented as ``dict[str, JsonSerializable]``
    - array: Represented as ``list[JsonSerializable]``

Thread Safety:
    Type aliases are inherently thread-safe as they are resolved at
    compile time and do not maintain state.

Example:
    >>> from omnibase_core.models.types.model_json_serializable import JsonSerializable
    >>>
    >>> # All of these are valid JsonSerializable values
    >>> string_value: JsonSerializable = "hello"
    >>> number_value: JsonSerializable = 42
    >>> nested_value: JsonSerializable = {
    ...     "name": "Alice",
    ...     "scores": [95, 87, 91],
    ...     "active": True,
    ...     "metadata": None,
    ... }

See Also:
    - omnibase_core.models.types: Package-level exports
    - omnibase_core.models.types.model_onex_common_types: Additional type aliases
"""

# JSON-serializable types that match JSON specification (RFC 8259).
# This recursive type alias represents all valid JSON values: strings, numbers,
# booleans, null, objects (dicts with string keys), and arrays.
# Used for type-safe serialization in contracts, API boundaries, and anywhere
# data must be JSON-compatible (e.g., event payloads, configuration values).
type JsonSerializable = (
    str
    | int
    | float
    | bool
    | None
    | dict[str, "JsonSerializable"]
    | list["JsonSerializable"]
)

__all__ = ["JsonSerializable"]
