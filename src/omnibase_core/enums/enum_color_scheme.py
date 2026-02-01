"""
Color scheme enumeration.

Defines color schemes for CLI output formatting.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumColorScheme(StrValueHelper, str, Enum):
    """
    Enumeration of color schemes for CLI output.

    Used for formatting and display purposes.
    """

    # Basic schemes
    DEFAULT = "default"
    NONE = "none"
    MONOCHROME = "monochrome"

    # Light themes
    LIGHT = "light"
    BRIGHT = "bright"
    PASTEL = "pastel"

    # Dark themes
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    TERMINAL = "terminal"

    # Themed schemes
    RAINBOW = "rainbow"
    OCEAN = "ocean"
    FOREST = "forest"
    SUNSET = "sunset"
    PROFESSIONAL = "professional"

    # Accessibility schemes
    COLORBLIND_FRIENDLY = "colorblind_friendly"
    HIGH_VISIBILITY = "high_visibility"

    @classmethod
    def get_accessible_schemes(cls) -> list[EnumColorScheme]:
        """Get list of accessibility-friendly color schemes."""
        return [
            cls.COLORBLIND_FRIENDLY,
            cls.HIGH_VISIBILITY,
            cls.HIGH_CONTRAST,
            cls.MONOCHROME,
        ]

    @classmethod
    def get_dark_schemes(cls) -> list[EnumColorScheme]:
        """Get list of dark color schemes."""
        return [
            cls.DARK,
            cls.HIGH_CONTRAST,
            cls.TERMINAL,
        ]

    @classmethod
    def get_light_schemes(cls) -> list[EnumColorScheme]:
        """Get list of light color schemes."""
        return [
            cls.LIGHT,
            cls.BRIGHT,
            cls.PASTEL,
            cls.DEFAULT,
        ]


# Export the enum
__all__ = ["EnumColorScheme"]
