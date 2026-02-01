"""Shared hex color validation for dashboard models.

This module provides centralized hex color validation used throughout
the ONEX dashboard models. It supports standard web color formats:
- #RGB (3 digits)
- #RRGGBB (6 digits)
- #RGBA (4 digits with alpha)
- #RRGGBBAA (8 digits with alpha)

Example:
    Using the validator in a Pydantic model::

        from pydantic import BaseModel, field_validator
        from omnibase_core.validation.validator_hex_color import validate_hex_color

        class ModelTheme(BaseModel):
            primary_color: str

            @field_validator("primary_color")
            @classmethod
            def check_color(cls, v: str) -> str:
                return validate_hex_color(v)

    Using the pattern directly for custom validation::

        from omnibase_core.validation.validator_hex_color import HEX_COLOR_PATTERN

        if HEX_COLOR_PATTERN.match(color):
            print("Valid hex color")
"""

import re
from collections.abc import Mapping
from typing import ClassVar

__all__ = (
    "HEX_COLOR_PATTERN",
    "HexColorValidator",
    "validate_hex_color",
    "validate_hex_color_optional",
    "validate_hex_color_mapping",
)

# Pre-compiled pattern for valid hex color formats: #RGB, #RRGGBB, #RGBA, #RRGGBBAA
# Thread-safe: re.Pattern objects are immutable, allowing safe concurrent access.
HEX_COLOR_PATTERN: re.Pattern[str] = re.compile(
    r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{8})$"
)

# Standard error message for invalid hex color format
_HEX_COLOR_ERROR_MSG = (
    "Invalid hex color format: {value}. Expected #RGB, #RRGGBB, #RGBA, or #RRGGBBAA"
)


class HexColorValidator:
    """Shared hex color validation for dashboard models.

    This class provides class-level validation methods for hex color codes.
    The pattern and methods are thread-safe as they use immutable compiled
    regex patterns.

    Attributes:
        PATTERN: Pre-compiled regex pattern for hex color validation.

    Example:
        Direct validation::

            HexColorValidator.validate("#FF0000")  # Returns "#FF0000"
            HexColorValidator.validate("invalid")  # Raises ValueError
    """

    PATTERN: ClassVar[re.Pattern[str]] = HEX_COLOR_PATTERN

    @classmethod
    def validate(cls, value: str) -> str:
        """Validate hex color format (#RGB, #RRGGBB, #RGBA, or #RRGGBBAA).

        Args:
            value: The color value to validate.

        Returns:
            The validated color value (unchanged).

        Raises:
            ValueError: If the value is not a valid hex color format.

        Example:
            >>> HexColorValidator.validate("#FF0000")
            '#FF0000'
            >>> HexColorValidator.validate("#F00")
            '#F00'
            >>> HexColorValidator.validate("invalid")
            ValueError: Invalid hex color format: invalid. Expected #RGB, #RRGGBB, #RGBA, or #RRGGBBAA
        """
        if not cls.PATTERN.fullmatch(value):
            # error-ok: Pydantic validators require ValueError
            raise ValueError(_HEX_COLOR_ERROR_MSG.format(value=value))
        return value

    @classmethod
    def validate_optional(cls, value: str | None) -> str | None:
        """Validate hex color format when value is optional.

        Args:
            value: The color value to validate, or None.

        Returns:
            The validated color value, or None if input was None.

        Raises:
            ValueError: If the value is not None and not a valid hex color format.

        Example:
            >>> HexColorValidator.validate_optional("#FF0000")
            '#FF0000'
            >>> HexColorValidator.validate_optional(None)
            None
        """
        if value is None:
            return None
        return cls.validate(value)

    @classmethod
    def validate_mapping(
        cls,
        mapping: Mapping[str, str],
        key_context: str = "key",
    ) -> Mapping[str, str]:
        """Validate all color values in a mapping.

        Args:
            mapping: A mapping of keys to hex color values.
            key_context: Context name for error messages (e.g., "status").

        Returns:
            The validated mapping (unchanged).

        Raises:
            ValueError: If any color value is not a valid hex format.

        Example:
            >>> colors = {"ok": "#00FF00", "error": "#FF0000"}
            >>> HexColorValidator.validate_mapping(colors, "status")
            {'ok': '#00FF00', 'error': '#FF0000'}
        """
        for key, color in mapping.items():
            if not cls.PATTERN.fullmatch(color):
                # error-ok: Pydantic validators require ValueError
                raise ValueError(
                    f"Invalid hex color format for {key_context} '{key}': {color}. "
                    "Expected #RGB, #RRGGBB, #RGBA, or #RRGGBBAA"
                )
        return mapping


# Convenience functions for direct use in Pydantic validators


def validate_hex_color(value: str) -> str:
    """Validate hex color format (#RGB, #RRGGBB, #RGBA, or #RRGGBBAA).

    This is a convenience function for use in Pydantic field validators.
    It wraps HexColorValidator.validate() for direct use.

    Args:
        value: The color value to validate.

    Returns:
        The validated color value (unchanged).

    Raises:
        ValueError: If the value is not a valid hex color format.

    Example:
        In a Pydantic model::

            @field_validator("color")
            @classmethod
            def check_color(cls, v: str) -> str:
                return validate_hex_color(v)
    """
    return HexColorValidator.validate(value)


def validate_hex_color_optional(value: str | None) -> str | None:
    """Validate hex color format when value is optional.

    This is a convenience function for use in Pydantic field validators
    where the color field may be None.

    Args:
        value: The color value to validate, or None.

    Returns:
        The validated color value, or None if input was None.

    Raises:
        ValueError: If the value is not None and not a valid hex color format.

    Example:
        In a Pydantic model::

            @field_validator("color")
            @classmethod
            def check_color(cls, v: str | None) -> str | None:
                return validate_hex_color_optional(v)
    """
    return HexColorValidator.validate_optional(value)


def validate_hex_color_mapping(
    mapping: Mapping[str, str],
    key_context: str = "key",
) -> Mapping[str, str]:
    """Validate all color values in a mapping.

    This is a convenience function for use in Pydantic field validators
    where colors are stored in a mapping (e.g., status_colors).

    Args:
        mapping: A mapping of keys to hex color values.
        key_context: Context name for error messages (e.g., "status").

    Returns:
        The validated mapping (unchanged).

    Raises:
        ValueError: If any color value is not a valid hex format.

    Example:
        In a Pydantic model::

            @field_validator("status_colors")
            @classmethod
            def check_colors(cls, v: Mapping[str, str]) -> Mapping[str, str]:
                return validate_hex_color_mapping(v, "status")
    """
    return HexColorValidator.validate_mapping(mapping, key_context)
