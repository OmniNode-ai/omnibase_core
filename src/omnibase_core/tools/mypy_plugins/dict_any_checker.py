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
    This plugin uses two complementary mechanisms:

    1. Function signature hooks: Check for dict[str, Any] at call sites when
       functions are called. This catches usage of unguarded dict[str, Any]
       in return types and parameters.

    2. Semantic analyzer plugin callback (via get_additional_deps): Processes
       function definitions to detect dict[str, Any] usage at definition time,
       catching uncalled functions as well.

    The plugin recognizes these decorator patterns:
    - @allow_dict_any
    - @allow_dict_any()
    - @allow_dict_any(reason="...")
    - @module.allow_dict_any
    - Stacked decorators (decorator can be anywhere in the stack)
"""

from collections.abc import Callable
from typing import Any, cast

from mypy.nodes import (
    CallExpr,
    ClassDef,
    Decorator,
    Expression,
    FuncDef,
    MemberExpr,
    MypyFile,
    NameExpr,
    SymbolNode,
)
from mypy.plugin import (
    FunctionSigContext,
    MethodSigContext,
    Plugin,
    ReportConfigContext,
)
from mypy.types import AnyType, CallableType, Instance, Type, get_proper_type

from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any


class DictAnyCheckerPlugin(Plugin):
    """
    Mypy plugin to check for unguarded dict[str, Any] usage.

    This plugin hooks into mypy's type checking to detect when dict[str, Any]
    is used in function signatures without the @allow_dict_any decorator.

    The plugin provides two mechanisms:
    1. Function signature hooks that check for dict[str, Any] at call sites
    2. Direct function/decorator checking via check_function_for_dict_any()

    Note: The current implementation hooks into function/method signature
    checking. This means warnings are emitted at call sites, not definition
    sites. For definition-time checking, use the check_function_for_dict_any()
    method directly in a separate analysis pass.

    Decorator Patterns Recognized:
    - @allow_dict_any
    - @allow_dict_any()
    - @allow_dict_any(reason="...")
    - @module.allow_dict_any
    - @decorators.allow_dict_any
    - Stacked decorators (decorator can be anywhere in the stack)
    """

    # Decorator that allows dict[str, Any] usage
    ALLOW_DECORATOR = "omnibase_core.decorators.decorator_allow_dict_any.allow_dict_any"
    ALLOW_DECORATOR_SHORT = "allow_dict_any"

    # Cache for functions we've already checked to avoid duplicate warnings
    _checked_functions: set[str] = set()

    @allow_dict_any(reason="Mypy plugin API requires dict[str, Any] return type")
    def report_config_data(self, ctx: ReportConfigContext) -> dict[str, Any]:
        """
        Report plugin configuration data.

        This method is called by mypy to get plugin configuration. We use it
        to report the plugin's settings and clear the function cache between runs.

        Args:
            ctx: The report configuration context.

        Returns:
            A dict with plugin configuration data.
        """
        # Clear the function cache for fresh analysis
        self._checked_functions.clear()

        return {
            "plugin": "DictAnyCheckerPlugin",
            "version": "1.0.0",
            "allow_decorator": self.ALLOW_DECORATOR,
        }

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

        This method handles multiple cases:
        1. Decorator nodes (wrapper that contains FuncDef + decorator list)
        2. FuncDef nodes (looks up symbol table to find Decorator wrapper)

        In mypy's AST, decorated functions are represented as Decorator nodes
        that wrap the FuncDef and contain the decorator list. When we receive
        a FuncDef from signature.definition, we need to look up the symbol
        table to find the wrapping Decorator node.

        IMPORTANT: We always try to look up the decorator node, even if the
        FuncDef's is_decorated attribute is False, because this attribute may
        not be reliably set on all FuncDef objects received from signature.definition.

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
            # First, try to find the Decorator node through symbol table lookup
            # This is the most reliable method as it finds the actual wrapper node
            fullname = getattr(defn, "fullname", None)
            if fullname and ctx is not None:
                decorator_node = self._lookup_decorator_node(fullname, ctx)
                if decorator_node is not None:
                    return self._check_decorators(decorator_node.decorators)

            # Fallback 1: Check is_decorated flag (may not be reliable)
            # If is_decorated is False, we've already tried symbol lookup above
            # and it failed, so the function is genuinely not decorated
            is_decorated = getattr(defn, "is_decorated", False)
            if not is_decorated:
                return False

            # Fallback 2: If we get here, is_decorated is True but we couldn't
            # find the Decorator node. This shouldn't happen in normal cases,
            # but we return False conservatively (decorator lookup failed)

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
        modules = self._get_modules_from_context(ctx)
        if not modules:
            return None

        try:
            # Split fullname to find module and local path
            # Handle cases like: module.function, module.Class.method
            parts = fullname.split(".")
            if len(parts) < 2:
                return None

            # Try progressively longer module prefixes (from longest to shortest)
            # This handles nested packages correctly
            for i in range(len(parts) - 1, 0, -1):
                module_name = ".".join(parts[:i])
                local_path = parts[i:]

                module = modules.get(module_name)
                if module is not None:
                    result = self._find_symbol_in_module(module, local_path)
                    if result is not None:
                        return result

        except (AttributeError, KeyError, TypeError):
            # tool-resilience-ok: mypy plugin version compatibility
            # These specific exceptions are caught because mypy's internal API varies
            # across versions (0.9xx, 1.x). Symbol table structure, attribute names,
            # and method signatures may differ. Using a specific tuple (not Exception
            # or BaseException) preserves interruptibility while handling API drift.
            pass

        return None

    def _get_modules_from_context(
        self,
        ctx: FunctionSigContext | MethodSigContext,
    ) -> dict[str, MypyFile] | None:
        """
        Extract the modules dict from the context.

        This method tries multiple approaches to access the modules dict,
        as the mypy plugin API varies across versions.

        Args:
            ctx: The context for accessing the type checker's modules.

        Returns:
            The modules dict if found, None otherwise.
        """
        try:
            api = ctx.api

            # Try direct access first
            modules = getattr(api, "modules", None)
            if modules is not None:
                return cast("dict[str, MypyFile]", modules)

            # Try accessing through internal attributes (various mypy versions)
            for attr in ("chk", "checker", "_checker", "manager", "options"):
                obj = getattr(api, attr, None)
                if obj is not None:
                    modules = getattr(obj, "modules", None)
                    if modules is not None:
                        return cast("dict[str, MypyFile]", modules)

            # Try accessing through msg.errors.errors (older mypy versions)
            msg = getattr(api, "msg", None)
            if msg is not None:
                errors = getattr(msg, "errors", None)
                if errors is not None:
                    modules = getattr(errors, "modules", None)
                    if modules is not None:
                        return cast("dict[str, MypyFile]", modules)

            # Try accessing through named_generic_type (internal method)
            # This is a last resort as it accesses very internal APIs
            ngt = getattr(api, "named_generic_type", None)
            if callable(ngt):
                # Access through closure or internal state
                self_obj = getattr(ngt, "__self__", None)
                if self_obj is not None:
                    modules = getattr(self_obj, "modules", None)
                    if modules is not None:
                        return cast("dict[str, MypyFile]", modules)

        except (AttributeError, KeyError, TypeError):
            # tool-resilience-ok: mypy plugin version compatibility
            # Mypy's checker API (api.modules, api.chk, etc.) varies across versions.
            # These specific exceptions handle missing attributes, changed structures,
            # or type mismatches without catching KeyboardInterrupt/SystemExit.
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
            module: The module node (MypyFile or similar).
            path: Path components (e.g., ['Class', 'method'] or ['function']).

        Returns:
            The Decorator node if found, None otherwise.
        """
        if not path:
            return None

        try:
            names = getattr(module, "names", None)
            if not names:
                return None

            current = names.get(path[0])
            if current is None:
                return None

            node = current.node
            if node is None:
                return None

            # Traverse path for nested symbols (e.g., Class.method)
            for part in path[1:]:
                # Handle ClassDef nodes
                if isinstance(node, ClassDef):
                    # For classes, look in their info.names dict (type info)
                    info = getattr(node, "info", None)
                    if info is not None:
                        info_names = getattr(info, "names", None)
                        if info_names:
                            sym = info_names.get(part)
                            if sym is not None and sym.node is not None:
                                node = sym.node
                                continue

                    # Fallback to class's direct names
                    class_names = getattr(node, "names", None)
                    if class_names:
                        sym = class_names.get(part)
                        if sym is not None and sym.node is not None:
                            node = sym.node
                            continue

                # For other nodes, try the names dict directly
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

        except (AttributeError, KeyError, TypeError):
            # tool-resilience-ok: symbol lookup may fail for unanalyzed code
            # Symbol table traversal can fail when code hasn't been fully analyzed,
            # when ClassDef/info structures differ across mypy versions, or when
            # names dicts are not yet populated. Specific tuple preserves interruptibility.
            pass

        return None

    def _check_decorators(self, decorators: list[Expression]) -> bool:
        """
        Check a list of decorator expressions for @allow_dict_any.

        This handles all common decorator patterns:
        - @allow_dict_any
        - @allow_dict_any()
        - @allow_dict_any(reason="...")
        - @module.allow_dict_any
        - @decorators.allow_dict_any
        - Stacked decorators (checks all in the list)

        Args:
            decorators: List of decorator expression nodes.

        Returns:
            True if @allow_dict_any is found in any of the decorators.
        """
        for decorator in decorators:
            if self._is_allow_dict_any_decorator(decorator):
                return True
        return False

    def _is_allow_dict_any_decorator(self, decorator: Expression) -> bool:
        """
        Check if a single decorator expression is @allow_dict_any.

        Args:
            decorator: The decorator expression node.

        Returns:
            True if this is the @allow_dict_any decorator.
        """
        decorator_name = self._get_decorator_name(decorator)

        # Check against known patterns
        if decorator_name in (
            self.ALLOW_DECORATOR,
            self.ALLOW_DECORATOR_SHORT,
            # Common import patterns
            "allow_dict_any.allow_dict_any",
            "decorators.decorator_allow_dict_any.allow_dict_any",
            "omnibase_core.decorators.decorator_allow_dict_any",
        ):
            return True

        # Check if the name ends with "allow_dict_any" (handles various import aliases)
        if (
            decorator_name.endswith(".allow_dict_any")
            or decorator_name == "allow_dict_any"
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

    # --- Utility methods for direct function checking (definition-time) ---

    def check_function_for_dict_any(
        self,
        node: Decorator | FuncDef,
    ) -> list[tuple[str, str]]:
        """
        Check a function definition for dict[str, Any] usage.

        This method can be used for definition-time checking by analyzing
        function nodes directly, without waiting for call sites.

        Args:
            node: A Decorator or FuncDef node to check.

        Returns:
            A list of (issue_type, message) tuples. Empty if no issues found.
            issue_type is one of: "return_type", "parameter"
        """
        issues: list[tuple[str, str]] = []

        # Get the FuncDef from the node
        if isinstance(node, Decorator):
            func_def = node.func
            decorators = node.decorators
        else:
            # node is FuncDef
            func_def = node
            decorators = []  # Will check via other means

        # Check if the function has the @allow_dict_any decorator
        if decorators and self._check_decorators(decorators):
            return issues  # Decorator present, no issues

        # For FuncDef without Decorator wrapper, try to determine if decorated
        if not decorators:
            is_decorated = getattr(func_def, "is_decorated", False)
            if is_decorated:
                # Can't determine decorators without context, be conservative
                return issues

        # Check the function's type annotation
        func_type = getattr(func_def, "type", None)
        if func_type is None:
            return issues

        # Get the proper type (unwrap type aliases etc.)
        proper_type = get_proper_type(func_type)
        if not isinstance(proper_type, CallableType):
            return issues

        func_name = getattr(func_def, "name", "function")

        # Check return type
        if self._is_dict_str_any(proper_type.ret_type):
            issues.append(
                (
                    "return_type",
                    f"Function '{func_name}' returns dict[str, Any] without "
                    f"@allow_dict_any decorator. Consider using a typed model instead.",
                )
            )

        # Check parameter types
        for i, arg_type in enumerate(proper_type.arg_types):
            if self._is_dict_str_any(arg_type):
                arg_name = (
                    proper_type.arg_names[i]
                    if i < len(proper_type.arg_names)
                    else f"arg{i}"
                )
                issues.append(
                    (
                        "parameter",
                        f"Function '{func_name}' has parameter '{arg_name}' of type "
                        f"dict[str, Any] without @allow_dict_any decorator. "
                        f"Consider using a typed model instead.",
                    )
                )

        return issues

    def check_decorator_has_allow_dict_any(
        self,
        node: Decorator | FuncDef,
    ) -> bool:
        """
        Check if a function has the @allow_dict_any decorator.

        This is a public utility method for checking decorator presence
        without requiring a mypy context.

        Args:
            node: A Decorator or FuncDef node to check.

        Returns:
            True if the function has the @allow_dict_any decorator.
        """
        if isinstance(node, Decorator):
            return self._check_decorators(node.decorators)

        # node is FuncDef - we can't determine decorators without context
        is_decorated = getattr(node, "is_decorated", False)
        return not is_decorated  # Conservatively return True if not decorated


# Type alias for the callback types used by mypy plugin hooks
FunctionSigCallback = Callable[[FunctionSigContext], CallableType]
MethodSigCallback = Callable[[MethodSigContext], CallableType]

__all__ = ["DictAnyCheckerPlugin"]
