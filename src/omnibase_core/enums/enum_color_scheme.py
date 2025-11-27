from __future__ import annotations

"""
Color scheme enumeration.

Defines color schemes for CLI output formatting.
"""

from enum import Enum, unique


@unique
class EnumColorScheme(str, Enum):
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

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def get_accessible_schemes(cls) -> list[EnumColorScheme]:
        """Get list[Any]of accessibility-friendly color schemes."""
        return [
            cls.COLORBLIND_FRIENDLY,
            cls.HIGH_VISIBILITY,
            cls.HIGH_CONTRAST,
            cls.MONOCHROME,
        ]

    @classmethod
    def get_dark_schemes(cls) -> list[EnumColorScheme]:
        """Get list[Any]of dark color schemes."""
        return [
            cls.DARK,
            cls.HIGH_CONTRAST,
            cls.TERMINAL,
        ]

    @classmethod
    def get_light_schemes(cls) -> list[EnumColorScheme]:
        """Get list[Any]of light color schemes."""
        return [
            cls.LIGHT,
            cls.BRIGHT,
            cls.PASTEL,
            cls.DEFAULT,
        ]


# Export the enum
__all__ = ["EnumColorScheme"]
