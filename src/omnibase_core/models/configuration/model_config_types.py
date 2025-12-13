"""Common types for configuration models."""

from typing import Literal, TypeGuard

# Type alias for valid configuration value types
ConfigValue = int | float | bool | str

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
    value_type: VALID_VALUE_TYPES, default: ConfigValue
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
