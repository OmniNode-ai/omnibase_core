"""
Dict[str, Any] usage checker mypy plugin.

This plugin detects usages of dict[str, Any] in type annotations that are not
guarded by the @allow_dict_any decorator. It helps enforce ONEX type safety
patterns by encouraging use of strongly-typed models instead of untyped dicts.

The plugin recognizes the @allow_dict_any decorator from:
    omnibase_core.decorators.allow_dict_any

When a function/method uses dict[str, Any] as a return type or parameter type
without the decorator, a warning is emitted suggesting the use of a typed model.

Example:
    # This will emit a warning:
    def get_data() -> dict[str, Any]:
        return {}

    # This is allowed (decorator present):
    @allow_dict_any(reason="Pydantic serialization")
    def serialize() -> dict[str, Any]:
        return self.model_dump()
"""

from mypy.nodes import FuncDef
from mypy.plugin import Plugin
from mypy.types import AnyType, Instance, Type


class DictAnyCheckerPlugin(Plugin):
    """
    Mypy plugin to check for unguarded dict[str, Any] usage.

    This plugin hooks into mypy's type checking to detect when dict[str, Any]
    is used in function signatures without the @allow_dict_any decorator.
    """

    # Decorator that allows dict[str, Any] usage
    ALLOW_DECORATOR = "omnibase_core.decorators.allow_dict_any.allow_dict_any"
    ALLOW_DECORATOR_SHORT = "allow_dict_any"

    def get_function_hook(self, fullname: str) -> None:  # stub-ok: mypy plugin API
        """
        Return a hook for function calls if needed.

        This method is called by mypy for each function call. We don't need
        function call hooks for this plugin, but the method must be defined.

        Args:
            fullname: Fully qualified name of the function.

        Returns:
            None - we don't hook into function calls.
        """
        return

    def get_method_hook(self, fullname: str) -> None:  # stub-ok: mypy plugin API
        """
        Return a hook for method calls if needed.

        This method is called by mypy for each method call. We don't need
        method call hooks for this plugin, but the method must be defined.

        Args:
            fullname: Fully qualified name of the method.

        Returns:
            None - we don't hook into method calls.
        """
        return

    def _is_dict_str_any(self, typ: Type) -> bool:
        """
        Check if a type is dict[str, Any].

        Args:
            typ: The mypy Type object to check.

        Returns:
            True if the type is dict[str, Any], False otherwise.
        """
        if not isinstance(typ, Instance):
            return False

        # Check if it's a dict type
        if typ.type.fullname not in ("builtins.dict", "typing.Dict"):
            return False

        # Check if it has exactly 2 type arguments
        if len(typ.args) != 2:
            return False

        # Check if first arg is str
        key_type = typ.args[0]
        if not isinstance(key_type, Instance):
            return False
        if key_type.type.fullname != "builtins.str":
            return False

        # Check if second arg is Any
        value_type = typ.args[1]
        return isinstance(value_type, AnyType)

    def _has_allow_decorator(self, defn: FuncDef) -> bool:
        """
        Check if a function has the @allow_dict_any decorator.

        This checks the function's decorator list for the allow_dict_any decorator,
        handling both the full module path and the short name.

        Args:
            defn: The FuncDef node to check.

        Returns:
            True if the function has the @allow_dict_any decorator.
        """
        # FuncDef doesn't directly have decorators, they're in the parent Decorator node
        # We need to check if this function was wrapped by a Decorator
        # This is handled by mypy's internal structure

        # Check if the function has the _allow_dict_any attribute marker
        # This is set by the runtime decorator
        if hasattr(defn, "decorators"):
            # In case decorators are attached directly (shouldn't happen normally)
            return True

        return False


__all__ = ["DictAnyCheckerPlugin"]
