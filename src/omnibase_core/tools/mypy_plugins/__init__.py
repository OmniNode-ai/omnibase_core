"""
ONEX mypy plugins package.

This package provides custom mypy plugins for enforcing ONEX type safety patterns.
Available plugins:

- dict_any_checker: Checks for unguarded dict[str, Any] usage

Usage in mypy.ini or pyproject.toml:
    [tool.mypy]
    plugins = ["omnibase_core.tools.mypy_plugins"]

The package exposes a plugin() function as required by mypy's plugin API.
"""

from mypy.plugin import Plugin


def plugin(version: str) -> type[Plugin]:
    """
    Mypy plugin entry point.

    This function is called by mypy to get the plugin class. It must be named
    'plugin' and return a Plugin subclass (specifically DictAnyCheckerPlugin).

    Args:
        version: The mypy version string (e.g., "1.19.0").

    Returns:
        The DictAnyCheckerPlugin class (a Plugin subclass) which mypy will instantiate.
    """
    # Import here to avoid circular imports and ensure proper initialization
    from omnibase_core.tools.mypy_plugins.dict_any_checker import DictAnyCheckerPlugin

    return DictAnyCheckerPlugin


__all__ = ["plugin"]
