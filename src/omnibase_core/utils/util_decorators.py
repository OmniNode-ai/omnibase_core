"""
Core decorators for model configuration.

Provides decorators for configuring Pydantic models with flexible typing
requirements for CLI and tool interoperability.
"""

from collections.abc import Callable
from typing import TypeVar

# TypeVar for any class type (not just Pydantic models)
# This allows the decorators to work with both Pydantic models and plain classes
ClassType = TypeVar("ClassType", bound=type)


def allow_any_type(reason: str) -> Callable[[ClassType], ClassType]:
    """
    Decorator to allow Any types in model fields.

    Args:
        reason: Explanation for why Any types are needed

    Returns:
        The decorator function
    """

    def decorator(cls: ClassType) -> ClassType:
        # Add metadata to the class for documentation
        if not hasattr(cls, "_allow_any_reasons"):
            cls._allow_any_reasons = []  # type: ignore[attr-defined]
        cls._allow_any_reasons.append(reason)  # type: ignore[attr-defined]
        return cls

    return decorator


def allow_dict_str_any(reason: str) -> Callable[[ClassType], ClassType]:
    """
    Decorator to allow dict[str, Any] types in model fields.

    Args:
        reason: Explanation for why dict[str, Any] is needed

    Returns:
        The decorator function
    """

    def decorator(cls: ClassType) -> ClassType:
        # Add metadata to the class for documentation
        if not hasattr(cls, "_allow_dict_str_any_reasons"):
            cls._allow_dict_str_any_reasons = []  # type: ignore[attr-defined]
        cls._allow_dict_str_any_reasons.append(reason)  # type: ignore[attr-defined]
        return cls

    return decorator
