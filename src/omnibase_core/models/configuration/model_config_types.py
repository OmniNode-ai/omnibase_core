"""
Configuration type aliases and validation utilities.

This module provides type definitions and validation for node configuration values,
enforcing type safety for configuration entries that support scalar types only
(int, float, bool, str).

Type Aliases:
    ScalarConfigValue: Union of valid scalar configuration value types.
        Excludes list, dict, and None to ensure simple, serializable config values.
    VALID_VALUE_TYPES: Literal type constraining type name strings to valid values.

Validation Functions:
    is_valid_value_type: TypeGuard for narrowing str to VALID_VALUE_TYPES.
    validate_config_value_type: Validates default value matches declared type.

Note:
    This module defines narrower types than the centralized ConfigValue in
    model_onex_common_types.py. Use ScalarConfigValue when only simple scalar
    values are acceptable (no list, dict, or None).

Example:
    >>> from omnibase_core.models.configuration.model_config_types import (
    ...     ScalarConfigValue,
    ...     is_valid_value_type,
    ...     validate_config_value_type,
    ... )
    >>> value: ScalarConfigValue = 42
    >>> if is_valid_value_type("int"):
    ...     validate_config_value_type("int", value)  # No error

See Also:
    - :class:`ModelNodeConfigEntry`: Configuration entry model using these types.
    - :class:`ModelNodeConfigSchema`: Configuration schema model using these types.
    - ConfigValue in model_onex_common_types.py: Broader type including list/dict/None.
"""

from typing import Literal, TypeGuard

# Type alias for valid scalar configuration value types
# Named ScalarConfigValue to distinguish from broader ConfigValue types
# that may include list[str] | dict[str, str] | None
ScalarConfigValue = int | float | bool | str

# Literal type constraining value_type/config_type to valid values
VALID_VALUE_TYPES = Literal["int", "float", "bool", "str"]

# Tuple of valid type names for runtime checking
_VALID_TYPE_NAMES: tuple[str, ...] = ("int", "float", "bool", "str")


def is_valid_value_type(type_name: str) -> TypeGuard[VALID_VALUE_TYPES]:
    """Type guard to check if a string is a valid value type.

    This function narrows the type of type_name from str to VALID_VALUE_TYPES
    when it returns True, enabling mypy to understand the type refinement.

    Args:
        type_name: The type name string to validate.

    Returns:
        True if type_name is one of 'int', 'float', 'bool', 'str'.
    """
    return type_name in _VALID_TYPE_NAMES


def validate_config_value_type(
    value_type: VALID_VALUE_TYPES, default: ScalarConfigValue
) -> None:
    """Validate that default value matches declared type.

    Args:
        value_type: The declared type ('int', 'float', 'bool', 'str')
        default: The default value to validate

    Raises:
        ValueError: If default value doesn't match declared type
    """
    type_map: dict[str, type | tuple[type, ...]] = {
        "int": int,
        "float": (int, float),  # int is valid for float
        "bool": bool,
        "str": str,
    }
    expected = type_map[value_type]
    # Strict bool check - don't allow int/float to match bool
    if value_type == "bool" and not isinstance(default, bool):
        raise ValueError(  # error-ok: Pydantic validator requires ValueError
            f"default must be bool, got {type(default).__name__}"
        )
    if not isinstance(default, expected):
        raise ValueError(  # error-ok: Pydantic validator requires ValueError
            f"default must be {value_type}, got {type(default).__name__}"
        )


__all__ = [
    "ScalarConfigValue",
    "VALID_VALUE_TYPES",
    "is_valid_value_type",
    "validate_config_value_type",
]
