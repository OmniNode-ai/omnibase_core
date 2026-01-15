"""
Allow dict[str, Any] Decorator

Provides a decorator to mark functions/methods that legitimately use dict[str, Any]
for ONEX validation purposes. This is a specialized version that works with both
simple pass-through usage and with reason arguments.

Usage:
    # Simple usage (no arguments)
    @allow_dict_any
    def serialize(self) -> dict[str, Any]:
        return self.model_dump()

    # With reason (for documentation)
    @allow_dict_any(reason="Serialization method for Pydantic compatibility")
    def to_dict(self) -> dict[str, Any]:
        return {...}
"""

from collections.abc import Callable
from typing import ParamSpec, TypeVar, overload

# Type variables for preserving function signatures
_P = ParamSpec("_P")
_R = TypeVar("_R")


@overload
def allow_dict_any(func: Callable[_P, _R]) -> Callable[_P, _R]: ...  # noqa: UP047


@overload
def allow_dict_any(
    func: None = None,
    *,
    reason: str | None = None,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]: ...


def allow_dict_any(  # noqa: UP047
    func: Callable[_P, _R] | None = None,
    *,
    reason: str | None = None,
) -> Callable[_P, _R] | Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """
    Decorator to allow dict[str, Any] usage in specific functions.

    This decorator is recognized by ONEX validation scripts and should only be used when:
    1. Serialization methods that must return dict[str, Any] for Pydantic compatibility
    2. Validator methods that accept raw untyped data before conversion
    3. Legacy integration where gradual typing is being applied

    Args:
        func: The function to decorate (when used without arguments)
        reason: Optional justification for using dict[str, Any] (when used with arguments)

    Returns:
        The decorated function with metadata attached

    Examples:
        # Simple usage without arguments
        @allow_dict_any
        def serialize(self) -> dict[str, Any]:
            return self.model_dump()

        # Usage with reason
        @allow_dict_any(reason="Serialization method for Pydantic compatibility")
        def to_dict(self) -> dict[str, Any]:
            return {"key": "value"}
    """

    def decorator(f: Callable[_P, _R]) -> Callable[_P, _R]:
        """Apply the decorator to a function."""
        # NOTE(OMN-1302): Dynamic attributes for decorator metadata tracking. Safe because read via getattr.
        f._allow_dict_any = True  # type: ignore[attr-defined]
        if reason:
            f._dict_any_reason = reason  # type: ignore[attr-defined]
        return f

    # Handle both @allow_dict_any and @allow_dict_any(reason="...")
    if func is not None:
        # Called as @allow_dict_any (without parentheses)
        return decorator(func)
    else:
        # Called as @allow_dict_any(...) (with parentheses and arguments)
        return decorator


__all__ = ["allow_dict_any"]
