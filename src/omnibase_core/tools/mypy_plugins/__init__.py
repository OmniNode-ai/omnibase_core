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
    'plugin' and return a Plugin subclass.

    Args:
        version: The mypy version string (e.g., "1.19.0"). Currently unused but
            required by the mypy plugin API for version compatibility checks.

    Returns:
        type[Plugin]: The DictAnyCheckerPlugin class which mypy will instantiate
            to enable dict[str, Any] usage checking.
    """
    # Import here to avoid circular imports and ensure proper initialization
    from omnibase_core.tools.mypy_plugins.dict_any_checker import DictAnyCheckerPlugin

    return DictAnyCheckerPlugin


__all__ = ["plugin"]
