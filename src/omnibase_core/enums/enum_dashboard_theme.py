"""Dashboard theme enumeration.

This module defines the available visual theme options for dashboards.
Themes control the color scheme and visual appearance of dashboard
widgets and layouts.

Example:
    Use theme in dashboard configuration::

        from omnibase_core.enums import EnumDashboardTheme

        # When creating a dashboard config, pass the theme:
        theme = EnumDashboardTheme.DARK
        # config = ModelDashboardConfig(..., theme=theme)
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ("EnumDashboardTheme",)


@unique
class EnumDashboardTheme(StrValueHelper, str, Enum):
    """Dashboard visual theme enumeration.

    Defines the available theme options for dashboard display. Themes
    affect widget backgrounds, text colors, chart colors, and other
    visual elements.

    Attributes:
        LIGHT: Light color scheme with white/light gray backgrounds
            and dark text. Suitable for well-lit environments.
        DARK: Dark color scheme with dark gray/black backgrounds
            and light text. Reduces eye strain in low-light environments.
        SYSTEM: Automatically follows the user's operating system
            theme preference. Enables seamless light/dark mode switching.

    Example:
        Check if theme is automatic::

            theme = EnumDashboardTheme.SYSTEM
            if theme.is_auto:
                print("Theme follows system preference")
    """

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"

    @property
    def is_auto(self) -> bool:
        """Check if theme follows system preference.

        When True, the dashboard will automatically switch between light
        and dark themes based on the user's OS preference.

        Returns:
            True if this is the SYSTEM theme, False for explicit
            LIGHT or DARK themes.
        """
        return self is EnumDashboardTheme.SYSTEM
