"""Common types for configuration models."""

from typing import Literal

# Type alias for valid configuration value types
ConfigValue = int | float | bool | str

# Literal type constraining value_type/config_type to valid values
VALID_VALUE_TYPES = Literal["int", "float", "bool", "str"]


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
