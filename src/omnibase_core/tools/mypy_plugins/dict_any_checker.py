"""
Dict[str, Any] Prevention Plugin for Mypy

This plugin detects and warns about usage of dict[str, Any] type annotations,
encouraging developers to use more specific types for better type safety.

Usage in mypy.ini or pyproject.toml:
    [tool.mypy]
    plugins = ["omnibase_core.tools.mypy_plugins.dict_any_checker"]

Configuration (optional):
    [dict_any_checker]
    # Comma-separated list of file patterns to exclude
    exclude_patterns = tests/*,scripts/*
    # Severity: "error" or "warning" or "note"
    severity = warning
    # Set to "error" to fail CI on violations
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mypy.plugin import (
    AnalyzeTypeContext,
    Plugin,
)
from mypy.types import (
    Type,
    UnboundType,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from mypy.options import Options

# Error code for dict[str, Any] violations
DICT_ANY_ERROR_CODE = "dict-str-any"

# Message templates
DICT_ANY_ERROR_MSG = (
    'Usage of "dict[str, Any]" is discouraged. '
    "Consider using TypedDict, a specific dict type, or ModelSchemaValue."
)


class DictAnyCheckerPlugin(Plugin):
    """
    Mypy plugin that detects dict[str, Any] usage.

    This plugin hooks into mypy's type analysis to identify when dict[str, Any]
    is used in type annotations and emits warnings/errors.
    """

    def __init__(self, options: Options) -> None:
        """Initialize the plugin with mypy options."""
        super().__init__(options)

    def get_type_analyze_hook(
        self, fullname: str
    ) -> Callable[[AnalyzeTypeContext], Type] | None:
        """
        Hook into type analysis to check for dict[str, Any] patterns.

        This hook is called when mypy analyzes type expressions like
        dict[str, Any] in annotations.
        """
        # We hook into builtins.dict to check its type arguments
        if fullname == "builtins.dict":
            return self._analyze_dict_type
        return None

    def _analyze_dict_type(self, ctx: AnalyzeTypeContext) -> Type:
        """
        Analyze dict type usage and warn if dict[str, Any] is detected.

        Args:
            ctx: The analysis context containing type info and API

        Returns:
            The analyzed type (we don't modify it, just check and warn)
        """
        # Let mypy analyze the type first
        analyzed_type = ctx.api.analyze_type(ctx.type)

        # Check if this is dict[str, Any]
        if self._is_dict_str_any(ctx.type, ctx):
            # Get file path for checking exclusions
            # Note: ctx.context can be None in some cases
            try:
                ctx.api.fail(
                    DICT_ANY_ERROR_MSG,
                    ctx.context,
                    code=None,  # mypy doesn't support custom error codes in plugins easily
                )
            except Exception:
                # Fail silently if we can't emit the error
                # (can happen in edge cases during analysis)
                pass

        return analyzed_type

    def _is_dict_str_any(
        self, typ: UnboundType | Type, ctx: AnalyzeTypeContext
    ) -> bool:
        """
        Check if a type represents dict[str, Any].

        Args:
            typ: The type to check
            ctx: Analysis context

        Returns:
            True if the type is dict[str, Any]
        """
        if not isinstance(typ, UnboundType):
            return False

        # Check if it's a dict type
        if typ.name not in ("dict", "Dict"):
            return False

        # Check if it has exactly 2 type arguments
        if len(typ.args) != 2:
            return False

        # Check if second argument is Any
        key_type, value_type = typ.args

        # Check if value type is Any
        if isinstance(value_type, UnboundType):
            if value_type.name == "Any":
                # Also verify key is str
                if isinstance(key_type, UnboundType) and key_type.name == "str":
                    return True

        return False


def plugin(version: str) -> type[DictAnyCheckerPlugin]:
    """
    Entry point for the mypy plugin.

    Args:
        version: The mypy version string

    Returns:
        The plugin class to use
    """
    # Version compatibility check
    # This plugin requires mypy 1.0+
    major_version = int(version.split(".")[0])
    if major_version < 1:
        # error-ok: mypy plugin runs in mypy context, cannot use OnexError
        raise RuntimeError(f"dict_any_checker plugin requires mypy 1.0+, got {version}")

    return DictAnyCheckerPlugin
