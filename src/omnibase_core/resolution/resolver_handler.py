"""
Handler Resolver - Resolve handler callables from import paths.

This module provides resolution of handler callables from fully qualified
import paths specified in contracts. Supports both eager and lazy import
patterns with caching for performance.

Handler Path Format:
    module.path:callable_name (colon-separated)

Examples:
    - myapp.handlers:handle_user_created
    - omnibase_core.nodes.handlers:process_effect

See Also:
    - OMN-1731: Contract-driven zero-code node base classes

.. versionadded:: 0.4.1
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Literal, Protocol, cast, overload

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class HandlerCallable(Protocol):
    """Protocol for handler callables with unknown signatures.

    This protocol allows any callable to be used as a handler. The __call__
    method accepts any arguments and returns object (the common supertype).

    Using Protocol avoids the `disallow_any_explicit` mypy error that would
    occur with `Callable[..., object]` where `...` is treated as explicit Any.
    """

    def __call__(self, *args: object, **kwargs: object) -> object:
        """Execute the handler with any arguments."""
        ...


# Type alias for lazy loader functions
LazyLoader = Callable[[], HandlerCallable]

# Module-level cache for resolved handlers
_handler_cache: dict[str, HandlerCallable] = {}


@overload
def resolve_handler(
    handler_path: str,
    *,
    eager: Literal[True] = ...,
) -> HandlerCallable: ...


@overload
def resolve_handler(
    handler_path: str,
    *,
    eager: Literal[False],
) -> LazyLoader: ...


def resolve_handler(
    handler_path: str,
    *,
    eager: bool = True,
) -> HandlerCallable | LazyLoader:
    """
    Resolve a handler callable by import path.

    Resolves a fully qualified handler path in the format "module.path:callable_name"
    to an actual callable. Supports both eager (immediate) and lazy (deferred)
    import patterns. Resolved handlers are cached for subsequent calls.

    Args:
        handler_path: Fully qualified path like "mymodule.handlers:handle_create".
            Must contain exactly one colon separating module path from callable name.
        eager: If True (default), import immediately and raise on failure.
            If False, return a lazy loader that defers import until first call.

    Returns:
        If eager=True: The resolved handler callable (HandlerCallable).
        If eager=False: A lazy loader function (LazyLoader) that returns
            the handler when called.

    Raises:
        ModelOnexError: If eager=True and handler cannot be resolved due to:
            - Invalid handler path format (missing or multiple colons)
            - Module import failure (ImportError)
            - Attribute not found in module (AttributeError)
            - Resolved attribute is not callable

    Example:
        >>> # Eager resolution (immediate import)
        >>> handler = resolve_handler("myapp.handlers:process_event")
        >>> result = handler(event_data)

        >>> # Lazy resolution (deferred import)
        >>> loader = resolve_handler("myapp.handlers:process_event", eager=False)
        >>> handler = loader()  # Import happens here
        >>> result = handler(event_data)

    Thread Safety:
        The handler cache is a module-level dict. While dict operations in CPython
        are atomic for simple get/set, concurrent resolution of the same handler
        may result in redundant imports. This is safe but potentially wasteful.
        For high-concurrency scenarios, consider external synchronization.

    .. versionadded:: 0.4.1
    """
    if not eager:
        # Return lazy loader that defers import until called
        def lazy_load() -> HandlerCallable:
            return resolve_handler(handler_path, eager=True)

        return lazy_load

    # Check cache first
    if handler_path in _handler_cache:
        return _handler_cache[handler_path]

    # Validate handler path format
    parts = handler_path.split(":")
    if len(parts) != 2:
        raise ModelOnexError(
            message=f"Invalid handler path format: '{handler_path}'. "
            "Expected format: 'module.path:callable_name'",
            error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
            handler_path=handler_path,
            expected_format="module.path:callable_name",
        )

    module_path, callable_name = parts

    if not module_path or not callable_name:
        raise ModelOnexError(
            message=f"Invalid handler path: '{handler_path}'. "
            "Both module path and callable name must be non-empty",
            error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
            handler_path=handler_path,
            module_path=module_path,
            callable_name=callable_name,
        )

    # Import the module
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise ModelOnexError(
            message=f"Failed to import module '{module_path}' for handler '{handler_path}'",
            error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
            handler_path=handler_path,
            module_path=module_path,
            original_error=str(e),
        ) from e

    # Get the callable from the module
    try:
        handler = getattr(module, callable_name)
    except AttributeError as e:
        raise ModelOnexError(
            message=f"Callable '{callable_name}' not found in module '{module_path}'",
            error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
            handler_path=handler_path,
            module_path=module_path,
            callable_name=callable_name,
            original_error=str(e),
        ) from e

    # Verify the attribute is callable
    if not callable(handler):
        raise ModelOnexError(
            message=f"Attribute '{callable_name}' in module '{module_path}' is not callable",
            error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
            handler_path=handler_path,
            module_path=module_path,
            callable_name=callable_name,
            actual_type=type(handler).__name__,
        )

    # Cast to proper type after callable() check confirms handler is callable.
    # getattr returns Any, but we've verified callable(handler) is True.
    typed_handler = cast(HandlerCallable, handler)

    # Cache and return
    _handler_cache[handler_path] = typed_handler
    return typed_handler


def clear_handler_cache() -> None:
    """
    Clear the handler cache.

    Removes all cached handler references. Useful for testing scenarios
    where module reloading is needed, or for freeing memory in long-running
    applications that dynamically load many handlers.

    Thread Safety:
        This operation clears the entire cache atomically (dict.clear()).
        Concurrent resolve_handler calls may re-populate the cache immediately.

    Example:
        >>> resolve_handler("myapp:handler")  # Cached
        >>> clear_handler_cache()  # Cache cleared
        >>> resolve_handler("myapp:handler")  # Re-imported

    .. versionadded:: 0.4.1
    """
    _handler_cache.clear()


__all__ = [
    "LazyLoader",
    "HandlerCallable",
    "clear_handler_cache",
    "resolve_handler",
]
