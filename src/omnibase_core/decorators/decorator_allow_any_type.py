"""
ONEX Decorator: Allow Any Type

Decorator to allow Any type usage in specific contexts where duck typing requires flexibility.
Used sparingly and only for duck typing utility functions.
"""

from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def allow_any_type(reason: str) -> Callable[[F], F]:
    """
    Decorator to allow Any type usage with documented reason.

    This decorator is used only for duck typing utilities where type flexibility
    is essential for protocol-agnostic object handling.

    Args:
        reason: Documented reason for allowing Any type usage

    Returns:
        Decorated function unchanged (documentation only)
    """

    def decorator(func: F) -> F:
        # NOTE(OMN-1302): Dynamic attribute for decorator metadata tracking. Safe because read via getattr.
        func.__allow_any_reason__ = reason  # type: ignore[attr-defined]
        return func

    return decorator
