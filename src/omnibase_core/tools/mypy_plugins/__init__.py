# SPDX-License-Identifier: Apache-2.0
"""Mypy plugins for ONEX type checking.

This module provides custom mypy plugins for enforcing ONEX-specific type checking
rules. The primary plugin, dict_any_checker, detects and warns about usage of
dict[str, Any] type annotations.

Usage in mypy.ini or pyproject.toml:
    [tool.mypy]
    plugins = ["omnibase_core.tools.mypy_plugins"]

Plugin Discovery:
    Mypy discovers plugins by looking for a callable named `plugin` at module level.
    This module re-exports the `plugin` function from dict_any_checker.
"""

from omnibase_core.tools.mypy_plugins.dict_any_checker import (
    DictAnyCheckerPlugin,
    plugin,
)

__all__ = ["DictAnyCheckerPlugin", "plugin"]
