"""Common types for configuration models."""

from typing import Literal

# Type alias for valid configuration value types
ConfigValue = int | float | bool | str

# Literal type constraining value_type/config_type to valid values
VALID_VALUE_TYPES = Literal["int", "float", "bool", "str"]
