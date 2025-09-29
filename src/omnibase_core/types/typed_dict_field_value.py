"""
TypedDict for field values.

This supports the field accessor pattern by providing strong typing
for field values without resorting to Any type usage.
"""

from typing import Any, TypedDict

from omnibase_core.core.type_constraints import (
    Configurable,
    Nameable,
    ProtocolValidatable,
    Serializable,
)


class TypedDictFieldValue(TypedDict, total=False):
    """Typed dictionary for field values.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    string_value: str
    int_value: int
    float_value: float
    bool_value: bool
    list_value: list[str]
