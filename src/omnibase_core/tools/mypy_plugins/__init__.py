"""
ONEX Mypy Plugins

Custom mypy plugins for ONEX-specific type checking rules.

Usage in mypy.ini or pyproject.toml:
    [tool.mypy]
    plugins = ["omnibase_core.tools.mypy_plugins"]

Or directly reference the specific plugin:
    plugins = ["omnibase_core.tools.mypy_plugins.dict_any_checker"]

Plugin Discovery:
    Mypy discovers plugins by looking for a callable named `plugin` at module level.
    This module re-exports the `plugin` function from dict_any_checker to enable
    loading via the package path.

    The `plugin` function signature must be:
        plugin(version: str) -> type[Plugin]

    Where `version` is the mypy version string and the return value is a Plugin class.
"""

from typing import TYPE_CHECKING

# Import the plugin function and class with proper error handling
try:
    from omnibase_core.tools.mypy_plugins.dict_any_checker import (
        DictAnyCheckerPlugin,
        plugin,
    )

    _PLUGIN_AVAILABLE = True
except ImportError as e:
    _PLUGIN_AVAILABLE = False
    _PLUGIN_IMPORT_ERROR = e

    # Provide a fallback plugin function that raises a clear error
    def plugin(version: str) -> type:  # type: ignore[misc]
        """Fallback plugin function when dict_any_checker import fails."""
        raise ImportError(  # error-ok: mypy plugin discovery requires ImportError
            f"Failed to load ONEX mypy plugin: {_PLUGIN_IMPORT_ERROR}. "
            "Ensure all dependencies are installed."
        )

    DictAnyCheckerPlugin = None  # type: ignore[assignment, misc]

if TYPE_CHECKING:
    from mypy.plugin import Plugin

# Export the plugin function and class for mypy discovery
__all__ = ["DictAnyCheckerPlugin", "plugin"]
