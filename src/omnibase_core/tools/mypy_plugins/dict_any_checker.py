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

Plugin Architecture:
    This plugin uses mypy's function signature hooks to check for dict[str, Any]
    usage. When a function with dict[str, Any] in its signature is called, the
    hook verifies whether the function definition has the @allow_dict_any decorator.

    Note: Due to mypy's plugin API design, hooks are triggered on function *calls*
    rather than function definitions. This means:
    1. Warnings appear at call sites, not definition sites
    2. Uncalled functions with dict[str, Any] won't trigger warnings
    3. This is consistent with mypy's type narrowing at call sites

    Future enhancement: A semantic analyzer plugin could check at definition time.
"""

from collections.abc import Callable
from typing import Any

from mypy.nodes import (
    CallExpr,
    Decorator,
    Expression,
    FuncDef,
    MemberExpr,
    NameExpr,
    SymbolNode,
)
from mypy.plugin import FunctionSigContext, MethodSigContext, Plugin
from mypy.types import AnyType, CallableType, Instance, Type


class DictAnyCheckerPlugin(Plugin):
    """
    Mypy plugin to check for unguarded dict[str, Any] usage.

    This plugin hooks into mypy's type checking to detect when dict[str, Any]
    is used in function signatures without the @allow_dict_any decorator.

    The plugin provides two mechanisms:
    1. Function signature hooks that check for dict[str, Any] at call sites
    2. Helper methods for decorator detection that can be used by other tools

    Note: The current implementation hooks into function/method signature
    checking. This means warnings are emitted at call sites, not definition
    sites. This is a limitation of mypy's plugin API - definition-time
    checking would require a semantic analyzer plugin.
    """

    # Decorator that allows dict[str, Any] usage
    ALLOW_DECORATOR = "omnibase_core.decorators.allow_dict_any.allow_dict_any"
    ALLOW_DECORATOR_SHORT = "allow_dict_any"

    # Cache for functions we've already checked to avoid duplicate warnings
    _checked_functions: set[str] = set()

    def get_function_hook(self, fullname: str) -> None:  # pyright: ignore[reportReturnType]  # stub-ok: mypy plugin API
        """
        Return a hook for function calls if needed.

        Note: This returns None because function *call* hooks are for modifying
        the return type of function calls (e.g., type narrowing). For signature
        checking, we use get_function_signature_hook instead.

        Args:
            fullname: Fully qualified name of the function.

        Returns:
            None - signature checking is done via get_function_signature_hook.
        """
        return

    def get_method_hook(self, fullname: str) -> None:  # pyright: ignore[reportReturnType]  # stub-ok: mypy plugin API
        """
        Return a hook for method calls if needed.

        Note: This returns None because method *call* hooks are for modifying
        the return type of method calls. For signature checking, we use
        get_method_signature_hook instead.

        Args:
            fullname: Fully qualified name of the method.

        Returns:
            None - signature checking is done via get_method_signature_hook.
        """
        return

    def get_function_signature_hook(
        self, fullname: str
    ) -> Callable[[FunctionSigContext], CallableType] | None:
        """
        Return a hook for checking function signatures.

        This hook is called when mypy processes a call to a function. We use it
        to check if the function uses dict[str, Any] without the @allow_dict_any
        decorator and emit a note if so.

        Args:
            fullname: Fully qualified name of the function being called.

        Returns:
            A callback that checks the signature, or None for non-matching functions.
        """
        # Check if this is a function we should inspect
        # We check all functions but only warn once per function
        if fullname in self._checked_functions:
            return None

        return self._check_function_signature

    def get_method_signature_hook(
        self, fullname: str
    ) -> Callable[[MethodSigContext], CallableType] | None:
        """
        Return a hook for checking method signatures.

        This hook is called when mypy processes a call to a method. We use it
        to check if the method uses dict[str, Any] without the @allow_dict_any
        decorator and emit a note if so.

        Args:
            fullname: Fully qualified name of the method being called.

        Returns:
            A callback that checks the signature, or None for non-matching methods.
        """
        # Check if this is a method we should inspect
        if fullname in self._checked_functions:
            return None

        return self._check_method_signature

    def _check_function_signature(self, ctx: FunctionSigContext) -> CallableType:
        """
        Check a function signature for dict[str, Any] usage.

        Args:
            ctx: The function signature context from mypy.

        Returns:
            The unmodified signature (we only emit notes, don't change types).
        """
        signature = ctx.default_signature
        self._check_signature_for_dict_any(signature, ctx)
        return signature

    def _check_method_signature(self, ctx: MethodSigContext) -> CallableType:
        """
        Check a method signature for dict[str, Any] usage.

        Args:
            ctx: The method signature context from mypy.

        Returns:
            The unmodified signature (we only emit notes, don't change types).
        """
        signature = ctx.default_signature
        self._check_signature_for_dict_any(signature, ctx)
        return signature

    def _check_signature_for_dict_any(
        self,
        signature: CallableType,
        ctx: FunctionSigContext | MethodSigContext,
    ) -> None:
        """
        Check a callable signature for dict[str, Any] usage.

        If dict[str, Any] is found in parameters or return type, check if the
        function has the @allow_dict_any decorator. If not, emit a note.

        Args:
            signature: The callable type to check.
            ctx: The context for emitting messages.
        """
        # Get the function definition if available
        defn = signature.definition
        if defn is None:
            return

        # Check if we've already processed this function
        fullname = getattr(defn, "fullname", None)
        if fullname and fullname in self._checked_functions:
            return

        if fullname:
            self._checked_functions.add(fullname)

        # Check if the function has the allow_dict_any decorator
        # Pass context to enable symbol table lookup for decorated functions
        if self._has_allow_decorator(defn, ctx):
            return

        # Check return type
        if self._is_dict_str_any(signature.ret_type):
            func_name = getattr(defn, "name", "function")
            ctx.api.fail(
                f"Function '{func_name}' returns dict[str, Any] without "
                f"@allow_dict_any decorator. Consider using a typed model instead.",
                ctx.context,
            )

        # Check parameter types
        for i, arg_type in enumerate(signature.arg_types):
            if self._is_dict_str_any(arg_type):
                func_name = getattr(defn, "name", "function")
                arg_name = (
                    signature.arg_names[i]
                    if i < len(signature.arg_names)
                    else f"arg{i}"
                )
                ctx.api.fail(
                    f"Function '{func_name}' has parameter '{arg_name}' of type "
                    f"dict[str, Any] without @allow_dict_any decorator. "
                    f"Consider using a typed model instead.",
                    ctx.context,
                )

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

    def _has_allow_decorator(
        self,
        defn: SymbolNode,
        ctx: FunctionSigContext | MethodSigContext | None = None,
    ) -> bool:
        """
        Check if a function has the @allow_dict_any decorator.

        This method handles two cases:
        1. Decorator nodes (wrapper that contains FuncDef + decorator list)
        2. FuncDef nodes (looks up symbol table to find Decorator wrapper)

        In mypy's AST, decorated functions are represented as Decorator nodes
        that wrap the FuncDef and contain the decorator list. When we receive
        a FuncDef from signature.definition, we need to look up the symbol
        table to find the wrapping Decorator node.

        Args:
            defn: The symbol node to check (can be FuncDef or Decorator).
            ctx: The context for accessing the type checker's symbol table.

        Returns:
            True if the function has the @allow_dict_any decorator.
        """
        # If this is a Decorator node, check its decorators list directly
        if isinstance(defn, Decorator):
            return self._check_decorators(defn.decorators)

        # If this is a FuncDef, we need to find the Decorator wrapper
        if isinstance(defn, FuncDef):
            # Quick check: if the function is not decorated, we can skip
            is_decorated = getattr(defn, "is_decorated", False)
            if not is_decorated:
                return False

            # Try to find the Decorator node through symbol table lookup
            fullname = getattr(defn, "fullname", None)
            if fullname and ctx is not None:
                decorator_node = self._lookup_decorator_node(fullname, ctx)
                if decorator_node is not None:
                    return self._check_decorators(decorator_node.decorators)

            # Fallback: check original_decorators if attached
            # (Some mypy versions may attach this after semantic analysis)
            original_decorators = getattr(defn, "original_decorators", None)
            if original_decorators:
                return self._check_decorators(original_decorators)

        return False

    def _lookup_decorator_node(
        self,
        fullname: str,
        ctx: FunctionSigContext | MethodSigContext,
    ) -> Decorator | None:
        """
        Look up the Decorator node from the symbol table.

        When a function is decorated, the symbol table entry contains the
        Decorator node (which wraps the FuncDef), but signature.definition
        returns the inner FuncDef. This method finds the Decorator wrapper
        by looking up the function in the symbol table.

        Args:
            fullname: The fully qualified name of the function.
            ctx: The context for accessing the type checker's modules.

        Returns:
            The Decorator node if found, None otherwise.
        """
        try:
            # Access the type checker's modules dict (internal API)
            api = ctx.api
            modules = getattr(api, "modules", None)

            # If not on api directly, try accessing through internal attributes
            if modules is None:
                # Some mypy versions expose modules through chk or other attrs
                for attr in ("chk", "checker", "_checker"):
                    obj = getattr(api, attr, None)
                    if obj is not None:
                        modules = getattr(obj, "modules", None)
                        if modules is not None:
                            break

            if not modules:
                return None

            # Split fullname to find module and local path
            # Handle cases like: module.function, module.Class.method
            parts = fullname.split(".")
            if len(parts) < 2:
                return None

            # Try progressively longer module prefixes
            for i in range(len(parts) - 1, 0, -1):
                module_name = ".".join(parts[:i])
                local_path = parts[i:]

                module = modules.get(module_name)
                if module is not None:
                    return self._find_symbol_in_module(module, local_path)

        except Exception:
            # Gracefully handle any API access issues
            pass

        return None

    def _find_symbol_in_module(
        self,
        module: Any,
        path: list[str],
    ) -> Decorator | None:
        """
        Find a symbol in a module by traversing the path.

        Args:
            module: The module node.
            path: Path components (e.g., ['Class', 'method'] or ['function']).

        Returns:
            The Decorator node if found, None otherwise.
        """
        try:
            names = getattr(module, "names", None)
            if not names:
                return None

            current = names.get(path[0])
            if current is None or current.node is None:
                return None

            node = current.node

            # Traverse path for nested symbols (e.g., Class.method)
            for part in path[1:]:
                # For classes, look in their names dict
                node_names = getattr(node, "names", None)
                if not node_names:
                    return None

                sym = node_names.get(part)
                if sym is None or sym.node is None:
                    return None
                node = sym.node

            # Return if we found a Decorator node
            if isinstance(node, Decorator):
                return node

        except Exception:
            pass

        return None

    def _check_decorators(self, decorators: list[Expression]) -> bool:
        """
        Check a list of decorator expressions for @allow_dict_any.

        Args:
            decorators: List of decorator expression nodes.

        Returns:
            True if @allow_dict_any is found in the decorators.
        """
        for decorator in decorators:
            decorator_name = self._get_decorator_name(decorator)
            if decorator_name in (
                self.ALLOW_DECORATOR,
                self.ALLOW_DECORATOR_SHORT,
                # Also check common import patterns
                "allow_dict_any.allow_dict_any",
            ):
                return True
        return False

    def _get_decorator_name(self, decorator: Expression) -> str:
        """
        Extract the name of a decorator from its AST node.

        Handles different decorator patterns:
        - @decorator (NameExpr)
        - @module.decorator (MemberExpr)
        - @decorator() or @decorator(args) (CallExpr wrapping the above)

        Args:
            decorator: The decorator expression node.

        Returns:
            The decorator name as a string, or empty string if unknown.
        """
        # Handle @decorator() or @decorator(args) - CallExpr wrapping a NameExpr/MemberExpr
        if isinstance(decorator, CallExpr):
            return self._get_decorator_name(decorator.callee)

        # Handle @decorator - simple name reference
        if isinstance(decorator, NameExpr):
            # Use fullname if available (resolved by semantic analysis)
            if decorator.fullname:
                return decorator.fullname
            return decorator.name

        # Handle @module.decorator - member expression
        if isinstance(decorator, MemberExpr):
            # Use fullname if available (resolved by semantic analysis)
            if decorator.fullname:
                return decorator.fullname
            # Fall back to constructing the name manually
            expr_name = self._get_expression_name(decorator.expr)
            if expr_name:
                return f"{expr_name}.{decorator.name}"
            return decorator.name

        return ""

    def _get_expression_name(self, expr: Expression) -> str:
        """
        Get the string representation of an expression for name resolution.

        Args:
            expr: The expression node.

        Returns:
            String representation of the expression, or empty string.
        """
        if isinstance(expr, NameExpr):
            return expr.name
        if isinstance(expr, MemberExpr):
            base = self._get_expression_name(expr.expr)
            if base:
                return f"{base}.{expr.name}"
            return expr.name
        return ""


# Type alias for the callback types used by mypy plugin hooks
FunctionSigCallback = Callable[[FunctionSigContext], CallableType]
MethodSigCallback = Callable[[MethodSigContext], CallableType]

__all__ = ["DictAnyCheckerPlugin"]
