# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Dashboard theme enumeration."""

from enum import Enum

__all__ = ["EnumDashboardTheme"]


class EnumDashboardTheme(str, Enum):
    """Dashboard theme preference.

    Defines the available theme options for dashboard display.
    """

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"

    @property
    def is_auto(self) -> bool:
        """Check if theme follows system preference."""
        return self == EnumDashboardTheme.SYSTEM
