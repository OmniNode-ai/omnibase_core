"""
ONEX Mypy Plugins

Custom mypy plugins for ONEX-specific type checking rules.

Usage in mypy.ini or pyproject.toml:
    [tool.mypy]
    plugins = ["omnibase_core.tools.mypy_plugins"]

Or directly reference the specific plugin:
    plugins = ["omnibase_core.tools.mypy_plugins.dict_any_checker"]
"""

from omnibase_core.tools.mypy_plugins.dict_any_checker import (
    DictAnyCheckerPlugin,
    plugin,
)

__all__ = ["DictAnyCheckerPlugin", "plugin"]
